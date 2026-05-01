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

from .mythos_preflight import run_preflight
from .post_build import create_github_repo, init_git_repo
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


async def synthesize(req: BuildRequest) -> BuildResult:
    """Render the template against the spec and write to disk.

    Returns a BuildResult with the absolute project path, file
    count, and human-readable next_steps the UI can show.

    Async because the optional Mythos pre-flight is async; the
    file-write loop itself is synchronous (local FS I/O is fast
    enough that asyncio.to_thread would just add overhead).
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

    # ── Post-build hooks (opt-in via flags) ─────────────────────
    git_initialized = False
    git_first_commit_sha = None
    github_repo_url = None
    post_build_warnings: list[str] = []

    if req.git_init:
        ok, sha, gw = init_git_repo(target, req.spec.project_name or "project")
        git_initialized = ok
        git_first_commit_sha = sha
        post_build_warnings.extend(gw)

        # Only attempt GH repo creation if git init succeeded —
        # `gh repo create --source=. --push` requires a working git
        # working tree.
        if req.github_repo_create and ok:
            url, gh_warn = create_github_repo(
                target,
                req.spec.project_name or "project",
                req.github_repo_visibility,
            )
            github_repo_url = url
            post_build_warnings.extend(gh_warn)
        elif req.github_repo_create and not ok:
            post_build_warnings.append(
                "skipped GitHub repo creation because git init failed"
            )
    elif req.github_repo_create:
        post_build_warnings.append(
            "github_repo_create requested but git_init was False; "
            "GitHub repo creation requires a local git repo first"
        )

    next_steps = [
        f"cd {target}",
        "Read README.md (root of the project) for the full quick-start.",
        "Set DATABASE_URL + JWT_SECRET in backend/.env",
        "Run backend/app/db/migrations/001_init.sql against your Postgres",
    ]
    if github_repo_url:
        next_steps.append(f"Visit your new repo: {github_repo_url}")
    elif git_initialized:
        next_steps.append("git status — your initial commit is on `main`")

    # ── Mythos pre-flight (opt-in via flag) ─────────────────────
    mythos = {
        "mythos_ran": False,
        "mythos_score": None,
        "mythos_critical_count": 0,
        "mythos_high_count": 0,
        "mythos_findings_summary": [],
    }
    if req.mythos_preflight:
        mythos = await run_preflight(target)
        if mythos["mythos_critical_count"] > 0:
            post_build_warnings.append(
                f"Mythos pre-flight: {mythos['mythos_critical_count']} CRITICAL "
                f"finding(s). See mythos_findings_summary."
            )
        if mythos["mythos_high_count"] > 0:
            post_build_warnings.append(
                f"Mythos pre-flight: {mythos['mythos_high_count']} HIGH "
                f"finding(s). See mythos_findings_summary."
            )

    # If post-build had warnings but the files are all on disk and
    # decryptable, the build is "partial" not "failed". Failed
    # only applies when the file write phase itself broke.
    has_any_warning = bool(warnings or post_build_warnings)
    overall_status = "complete" if not has_any_warning else "partial"

    return BuildResult(
        project_path=str(target),
        files_written=written,
        template_id=req.template_id,
        status=overall_status,
        next_steps=next_steps,
        warnings=warnings,
        git_initialized=git_initialized,
        git_first_commit_sha=git_first_commit_sha,
        github_repo_url=github_repo_url,
        post_build_warnings=post_build_warnings,
        **mythos,
    )
