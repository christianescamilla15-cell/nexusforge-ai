"""Mythos pre-flight scan over a freshly-generated project.

Runs the existing `MythosScanner` (the same one that audits
NexusForge itself) against the target directory. Returns a
compact summary that surfaces critical/high findings to the
build response so the user knows BEFORE running the project if
the template introduced something bad.

Why this matters:
  - First-party templates (the four shipped today) are reviewed
    code; a fresh scan should yield ~0 findings. This module is
    a regression test that fires every time someone touches a
    template's render function.
  - When third-party templates land later, this is the trust
    boundary. The synthesizer will not run unsafe code on the
    user's machine without a Mythos audit first.

Out of scope (for now):
  - Severity gating that REFUSES the build on critical findings.
    Today we surface them as warnings and let the user decide.
    A future enhancement could expose `mythos_strict: bool` on
    BuildRequest that turns the build into status="failed" if
    any critical/high lands.
  - Pinning a "known-clean" baseline per template. Mythos has
    baseline-aware mode used in NexusForge itself, but for
    generated projects there's no historical baseline to compare
    against — every scan is from scratch.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_preflight(target: Path) -> dict:
    """Scan the generated project. Returns a compact dict ready
    to merge into BuildResult.

    Always returns a structurally-valid dict — never raises. A
    Mythos failure (import error, scanner exception, timeout)
    surfaces as `mythos_ran: False` with a warning so the build
    completes.
    """
    base = {
        "mythos_ran": False,
        "mythos_score": None,
        "mythos_critical_count": 0,
        "mythos_high_count": 0,
        "mythos_findings_summary": [],
    }

    try:
        from app.security.mythos import MythosScanner
    except Exception as exc:
        logger.warning("Mythos pre-flight: scanner import failed: %s", exc)
        return {**base, "mythos_findings_summary": [f"scanner unavailable: {exc}"]}

    try:
        scanner = MythosScanner(str(target))
        report = await scanner.full_scan()
    except Exception as exc:
        logger.warning("Mythos pre-flight: scan raised %s", exc)
        return {**base, "mythos_findings_summary": [f"scan errored: {type(exc).__name__}: {exc}"]}

    # Aggregate by severity.
    crit_count = 0
    high_count = 0
    summary: list[str] = []
    for f in report.findings:
        sev = (f.severity or "").lower()
        if sev == "critical":
            crit_count += 1
        elif sev == "high":
            high_count += 1
        if sev in ("critical", "high"):
            # Compact one-liner: severity + title + relative file path.
            file_part = f""
            if f.file_path:
                try:
                    rel = Path(f.file_path).relative_to(target)
                    file_part = f" — {rel}:{f.line_number}" if f.line_number else f" — {rel}"
                except ValueError:
                    file_part = f" — {f.file_path}"
            summary.append(f"[{sev}] {f.title}{file_part}")

    # Cap the summary so the response payload doesn't balloon if
    # something goes really wrong.
    if len(summary) > 20:
        truncated = len(summary) - 20
        summary = summary[:20]
        summary.append(f"… and {truncated} more (run /api/mythos/scan for full report)")

    score = report.to_dict().get("score")

    return {
        "mythos_ran": True,
        "mythos_score": score,
        "mythos_critical_count": crit_count,
        "mythos_high_count": high_count,
        "mythos_findings_summary": summary,
    }
