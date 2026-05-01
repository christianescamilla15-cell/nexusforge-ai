"""Project synthesizer — turns a finalized spec + template into a
real directory of files on disk.

Security posture:
  - The target directory is REQUIRED to live under a configured
    root (``PLATFORM_SYNTH_ROOT`` env var, falls back to
    ``~/nexusforge-generated``). Every absolute path is canonicalized
    and checked against the root before any write. Path traversal
    via ``..`` is rejected.
  - The target directory must NOT already exist OR must be empty
    (no overwriting existing project trees by accident).
  - Each file is written with normal permissions (0o644 / 0o755 for
    none of these; we don't emit executables in v1).

This module is intentionally synchronous — disk I/O on local FS
isn't worth the asyncio complexity for this volume of files.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .schemas import BuildRequest, BuildResult
from .templates import get_template

logger = logging.getLogger(__name__)


def _resolve_synth_root() -> Path:
    """Return the configured root that all generated projects must
    live under. Resolved + canonicalized."""
    root_str = os.environ.get("PLATFORM_SYNTH_ROOT")
    if root_str:
        root = Path(root_str).expanduser().resolve()
    else:
        root = (Path.home() / "nexusforge-generated").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _validate_target(target_dir: str) -> Path:
    """Resolve `target_dir` and assert it falls under the synth root.

    Returns the validated Path. Raises ValueError on traversal.
    """
    root = _resolve_synth_root()
    target = Path(target_dir).expanduser().resolve()

    # Must be a child of root (or root itself, though that's silly).
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(
            f"target_dir must be under {root!s}; got {target!s}"
        )

    if target.exists() and any(target.iterdir()):
        raise ValueError(
            f"target_dir {target!s} already exists and is not empty — refusing to overwrite"
        )

    return target


def synthesize(req: BuildRequest) -> BuildResult:
    """Render the template against the spec and write to disk.

    Returns a BuildResult with the absolute project path, file
    count, and human-readable next_steps the UI can show.
    """
    summary, render = get_template(req.template_id)

    # Render — may raise ValueError("project_name is required ...") etc.
    files = render(req.spec)

    target = _validate_target(req.target_dir)
    target.mkdir(parents=True, exist_ok=True)

    written = 0
    warnings: list[str] = []

    for relative_path, content in files.items():
        # Normalize separators and reject path traversal in template
        # output (defense in depth — templates ship trusted, but a
        # future template author could regress).
        if "\\" in relative_path:
            relative_path = relative_path.replace("\\", "/")
        parts = [p for p in relative_path.split("/") if p and p != "."]
        if any(p == ".." for p in parts):
            warnings.append(f"skipped suspicious path: {relative_path!r}")
            continue

        out = target.joinpath(*parts)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        written += 1

    next_steps = [
        f"cd {target}",
        "Read README.md (root of the project) for the full quick-start.",
        "Set DATABASE_URL + JWT_SECRET in backend/.env",
        "Run backend/app/db/migrations/001_init.sql against your Postgres",
    ]

    return BuildResult(
        project_path=str(target),
        files_written=written,
        template_id=req.template_id,
        status="complete" if not warnings else "partial",
        next_steps=next_steps,
        warnings=warnings,
    )
