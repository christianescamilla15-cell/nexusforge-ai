"""PR Generator — auto-create pull requests from refactoring results.

Creates one PR per module/fix-type with:
  - Branch per fix category
  - Commit with descriptive message
  - PR description with findings + fixes + test results
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# M-4 (2026-04-25): NexusForge's own repo root (resolved at import).
# generate_pr refuses to operate against this path (or any subdir of
# it) so a malicious or mistakenly-pointed call cannot dirty the
# running server's git state.
_NEXUSFORGE_ROOT = Path(__file__).resolve().parents[3]

# Strict branch-suffix validation: only `[a-zA-Z0-9._-]` allowed, no
# leading dash (avoids `--option` smuggling into git argv).
_BRANCH_SAFE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9._-]*$")


class PRGenerator:
    """Generate git branches and PRs from refactoring results."""

    def __init__(self, repo_path: str):
        self.repo = Path(repo_path).resolve()
        # M-4: refuse to operate against NexusForge's own working tree
        # — that would `git checkout -b` on the running server.
        try:
            self.repo.relative_to(_NEXUSFORGE_ROOT)
        except ValueError:
            pass  # repo is OUTSIDE NexusForge — safe
        else:
            raise RuntimeError(
                f"PR generator refuses to operate inside the NexusForge "
                f"repo itself (path={self.repo})"
            )

    async def generate_pr(
        self,
        report: "RefactorReport",
        base_branch: str = "main",
        prefix: str = "nexusforge/fix",
    ) -> dict:
        """Create a PR-ready branch with all fixes.

        Args:
            report: RefactorReport from RefactoringEngine
            base_branch: Branch to base PR on
            prefix: Branch name prefix

        Returns:
            {branch, files_changed, commit_message, pr_body}
        """
        fixed_files = [r for r in report.results if r.status == "fixed"]
        if not fixed_files:
            return {"status": "no_fixes", "message": "No files were fixed"}

        # M-4: validate `report.project_name` before splicing into git
        # argv. project_name comes from `Path(repo).name` ultimately,
        # but a path with shell-meta or git-ref-meta (`../`, ` -- `)
        # could result in surprising git behavior.
        if not _BRANCH_SAFE.match(report.project_name or ""):
            return {
                "status": "error",
                "message": f"project_name {report.project_name!r} contains "
                           "characters not allowed in a branch name",
            }
        branch_name = f"{prefix}/{report.project_name}-security"
        commit_msg = self._build_commit_message(report)
        pr_body = self._build_pr_body(report)

        try:
            # Create branch
            await self._run_git("checkout", "-b", branch_name)

            # Stage all fixed files
            for r in fixed_files:
                await self._run_git("add", r.file_path)

            # Commit
            await self._run_git("commit", "-m", commit_msg)

            logger.info("PR branch created: %s with %d files", branch_name, len(fixed_files))

            return {
                "status": "ready",
                "branch": branch_name,
                "base": base_branch,
                "files_changed": len(fixed_files),
                "commit_message": commit_msg,
                "pr_title": f"security: fix {report.vulnerabilities_fixed} vulnerabilities across {len(fixed_files)} files",
                "pr_body": pr_body,
            }
        except Exception as exc:
            logger.error("PR generation failed: %s", exc)
            # Cleanup: go back to base branch
            try:
                await self._run_git("checkout", base_branch)
            except Exception:
                pass
            return {"status": "error", "message": str(exc)[:200]}

    def _build_commit_message(self, report: "RefactorReport") -> str:
        fix_types = set()
        for r in report.results:
            if r.status == "fixed":
                fix_types.add(r.fix_type)

        types_str = ", ".join(sorted(fix_types)[:5])
        return (
            f"security: fix {report.vulnerabilities_fixed} vulnerabilities\n\n"
            f"Automated refactoring by NexusForge AI:\n"
            f"- Files fixed: {report.files_fixed}\n"
            f"- Fix types: {types_str}\n"
            f"- Tests passing: {report.tests_passing}/{report.files_fixed}\n"
            f"- Duration: {report.duration_ms}ms\n"
            f"- Cost: ${report.total_cost_usd:.4f}"
        )

    def _build_pr_body(self, report: "RefactorReport") -> str:
        fixed = [r for r in report.results if r.status == "fixed"]
        failed = [r for r in report.results if r.status in ("failed", "test_failed")]

        body = f"""## Security Refactoring — {report.project_name}

### Summary
- **{report.vulnerabilities_fixed}** vulnerabilities fixed across **{report.files_fixed}** files
- **{report.tests_passing}** tests passing
- **{report.files_failed}** files need manual review
- Duration: {report.duration_ms}ms | Cost: ${report.total_cost_usd:.4f}

### Files Fixed
| File | Fix Type | Diff Lines | Tests |
|------|----------|-----------|-------|
"""
        for r in fixed[:30]:
            test_icon = "pass" if r.tests_passed else "FAIL"
            body += f"| `{r.file_path}` | {r.fix_type} | +{r.diff_lines} | {test_icon} |\n"

        if failed:
            body += "\n### Files Needing Manual Review\n"
            for r in failed[:10]:
                body += f"- `{r.file_path}`: {r.error or r.status}\n"

        body += "\n---\nGenerated by [NexusForge AI](https://nexusforge-two.vercel.app)\n"
        return body

    async def _run_git(self, *args):
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=str(self.repo),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {stderr.decode()[:200]}")
        return stdout.decode()
