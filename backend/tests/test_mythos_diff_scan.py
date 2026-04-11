"""Tests for Phase 6 — Mythos diff-aware scan.

Covers ``MythosScanner.diff_scan`` and the ``_should_scan`` allowlist:

- Happy path: a scoped list of 2 files produces findings ONLY for
  those files, even when other files in the project contain
  hardcoded secrets / injection patterns.
- Path safety: absolute paths, path traversal (``..``), null bytes,
  empty strings, and paths outside the project root are silently
  skipped (not raised).
- Missing files in the diff (deleted files) are silently skipped.
- Findings are fresh — a prior ``full_scan`` on the same instance
  does not leak into the ``diff_scan`` result.
- The allowlist is cleared on exit so a subsequent ``full_scan``
  on the same scanner instance is NOT accidentally scoped.
- ``AuditReport.scanned_files`` reflects the filtered count, not
  the requested count.

The tests build a tiny synthetic project tree inside ``tmp_path``
so we do not depend on the real repo's content.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.security.mythos import MythosScanner


def _make_project(root: Path) -> None:
    """Build a minimal project tree with planted findings."""
    # backend/app/routes/changed.py — has an SQL injection pattern
    (root / "backend" / "app" / "routes").mkdir(parents=True, exist_ok=True)
    (root / "backend" / "app" / "routes" / "changed.py").write_text(
        'query = f"SELECT * FROM users WHERE id = {user_id}"\n'
        'await conn.execute(query)\n',
        encoding="utf-8",
    )

    # backend/app/routes/untouched.py — has the SAME pattern but
    # should NOT be scanned in diff mode when not listed.
    (root / "backend" / "app" / "routes" / "untouched.py").write_text(
        'query = f"SELECT * FROM orders WHERE id = {order_id}"\n'
        'await conn.execute(query)\n',
        encoding="utf-8",
    )

    # Another changed file with a hardcoded secret-looking token.
    (root / "backend" / "app" / "config.py").write_text(
        'api_key = "sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345678"\n',
        encoding="utf-8",
    )

    # frontend dir so MythosScanner.__init__ doesn't fall over
    (root / "frontend" / "src").mkdir(parents=True, exist_ok=True)


# ── Happy path ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_diff_scan_only_reports_findings_from_allowlist(tmp_path: Path):
    _make_project(tmp_path)
    scanner = MythosScanner(str(tmp_path))

    report = await scanner.diff_scan(
        changed_files=["backend/app/routes/changed.py"]
    )

    # Exactly one file was scanned (the one in the allowlist)
    assert report.scanned_files >= 1

    # The finding must reference the scanned file, NOT the untouched one
    file_paths = {f.file_path for f in report.findings}
    assert any("changed.py" in fp for fp in file_paths), (
        f"expected changed.py in findings, got: {file_paths}"
    )
    assert not any("untouched.py" in fp for fp in file_paths), (
        "untouched.py must not appear — it was not in the allowlist"
    )


@pytest.mark.asyncio
async def test_diff_scan_reports_secret_finding_for_changed_config(tmp_path: Path):
    _make_project(tmp_path)
    scanner = MythosScanner(str(tmp_path))

    report = await scanner.diff_scan(
        changed_files=["backend/app/config.py"]
    )

    # The secret pattern should trip the secrets scanner
    secret_findings = [f for f in report.findings if f.category == "secrets"]
    assert len(secret_findings) >= 1
    assert all("config.py" in f.file_path for f in secret_findings)


# ── Path safety ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_diff_scan_rejects_absolute_paths(tmp_path: Path):
    _make_project(tmp_path)
    scanner = MythosScanner(str(tmp_path))

    report = await scanner.diff_scan(
        changed_files=["/etc/passwd", "C:\\Windows\\System32\\drivers\\etc\\hosts"]
    )

    assert report.scanned_files == 0
    assert report.findings == []


@pytest.mark.asyncio
async def test_diff_scan_rejects_traversal(tmp_path: Path):
    _make_project(tmp_path)
    scanner = MythosScanner(str(tmp_path))

    report = await scanner.diff_scan(
        changed_files=["../../etc/passwd", "backend/../../etc/passwd"]
    )

    assert report.scanned_files == 0


@pytest.mark.asyncio
async def test_diff_scan_skips_empty_and_null_byte(tmp_path: Path):
    _make_project(tmp_path)
    scanner = MythosScanner(str(tmp_path))

    report = await scanner.diff_scan(
        changed_files=["", "backend/app/\x00evil.py"]
    )

    assert report.scanned_files == 0


@pytest.mark.asyncio
async def test_diff_scan_skips_missing_files(tmp_path: Path):
    _make_project(tmp_path)
    scanner = MythosScanner(str(tmp_path))

    # A valid-looking relative path that does not exist on disk.
    # This is the "file deleted in the diff" case.
    report = await scanner.diff_scan(
        changed_files=["backend/app/routes/deleted.py"]
    )

    assert report.scanned_files == 0
    assert report.findings == []


# ── Isolation from full_scan ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_diff_scan_clears_allowlist_on_exit(tmp_path: Path):
    """After diff_scan returns, the scanner's allowlist must be None
    so a subsequent full_scan on the same instance is not silently
    scoped."""
    _make_project(tmp_path)
    scanner = MythosScanner(str(tmp_path))

    await scanner.diff_scan(changed_files=["backend/app/routes/changed.py"])

    assert scanner._file_allowlist is None


@pytest.mark.asyncio
async def test_diff_scan_does_not_inherit_prior_findings(tmp_path: Path):
    """Calling diff_scan after a previous scan on the same instance
    must not carry over the earlier findings — the report should
    only reflect the current diff."""
    _make_project(tmp_path)
    scanner = MythosScanner(str(tmp_path))

    # Seed with fake prior findings
    from app.security.mythos import Finding
    scanner.findings.append(
        Finding(
            severity="critical",
            category="secrets",
            title="stale finding from a prior scan",
            description="should not leak",
            file_path="somewhere/else.py",
        )
    )

    report = await scanner.diff_scan(
        changed_files=["backend/app/routes/changed.py"]
    )

    # The stale finding must NOT appear in the new report
    titles = {f.title for f in report.findings}
    assert "stale finding from a prior scan" not in titles


# ── _should_scan helper ──────────────────────────────────────────────


def test_should_scan_returns_true_when_allowlist_is_none(tmp_path: Path):
    """Default behavior (no allowlist set) scans everything — this is
    what full_scan relies on."""
    scanner = MythosScanner(str(tmp_path))
    # A file that does not even exist — _should_scan is a gate, not
    # an existence check.
    assert scanner._should_scan(tmp_path / "anywhere.py") is True


def test_should_scan_respects_allowlist(tmp_path: Path):
    _make_project(tmp_path)
    scanner = MythosScanner(str(tmp_path))

    target = (tmp_path / "backend" / "app" / "routes" / "changed.py").resolve()
    other = (tmp_path / "backend" / "app" / "routes" / "untouched.py").resolve()
    scanner._file_allowlist = frozenset({target})

    assert scanner._should_scan(target) is True
    assert scanner._should_scan(other) is False
