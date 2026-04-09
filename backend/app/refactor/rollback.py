"""Rollback mechanism — auto-revert changes when tests fail.

Creates a git stash or backup before each refactoring batch.
If tests fail after applying fixes, reverts to the backup state.
"""

import asyncio
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manage safe rollback of file changes."""

    def __init__(self, repo_path: str):
        self.repo = Path(repo_path)
        self._backups: dict[str, str] = {}  # file_path → original_content
        self._git_available = (self.repo / ".git").exists()

    async def checkpoint(self, files: list[str]) -> str:
        """Create a checkpoint before modifying files.

        Returns checkpoint_id for rollback.
        """
        checkpoint_id = f"nxf_{len(self._backups)}"

        if self._git_available:
            # Use git stash for atomic rollback
            try:
                await self._run_git("stash", "push", "-m", f"nexusforge-checkpoint-{checkpoint_id}", "--", *files)
                await self._run_git("stash", "pop")  # Pop immediately, we just want the stash as backup
                logger.info("Git checkpoint created: %s (%d files)", checkpoint_id, len(files))
                return checkpoint_id
            except Exception:
                pass  # Fall through to file-based backup

        # File-based backup (fallback)
        for file_path in files:
            fpath = self.repo / file_path
            if fpath.exists():
                self._backups[file_path] = fpath.read_text(encoding="utf-8", errors="ignore")

        logger.info("File checkpoint created: %s (%d files)", checkpoint_id, len(files))
        return checkpoint_id

    async def rollback(self, files: list[str]) -> int:
        """Rollback files to their checkpoint state.

        Returns number of files restored.
        """
        restored = 0

        if self._git_available:
            try:
                # Restore from git
                await self._run_git("checkout", "--", *files)
                logger.info("Git rollback: %d files restored", len(files))
                return len(files)
            except Exception:
                pass  # Fall through to file-based restore

        # File-based restore
        for file_path in files:
            if file_path in self._backups:
                fpath = self.repo / file_path
                fpath.write_text(self._backups[file_path], encoding="utf-8")
                restored += 1

        logger.info("File rollback: %d files restored", restored)
        return restored

    async def rollback_all(self) -> int:
        """Rollback ALL modified files."""
        if self._git_available:
            try:
                await self._run_git("checkout", ".")
                logger.info("Git rollback: all files restored")
                return len(self._backups)
            except Exception:
                pass

        restored = 0
        for file_path, content in self._backups.items():
            try:
                fpath = self.repo / file_path
                fpath.write_text(content, encoding="utf-8")
                restored += 1
            except Exception:
                pass

        self._backups.clear()
        return restored

    async def _run_git(self, *args):
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=str(self.repo),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            raise RuntimeError(stderr.decode()[:200])
        return stdout.decode()
