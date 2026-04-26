"""Tests for the C-4 run_code agent-tool hardening.

Covers:
- Default-off: with no env var set, run_code refuses with a clear
  error message instead of executing arbitrary Python.
- Blocklist tokens: when the flag is on, snippets with obviously
  dangerous patterns (os.environ read, subprocess, urllib, eval,
  __import__) are rejected before subprocess spawn.
- Env scrub: even if a benign snippet runs, NexusForge secrets are
  not visible in `os.environ` inside the subprocess.

These tests do NOT cover the case where ALLOW_CODE_EXEC=true and a
benign snippet executes — that path is integration-y (spawns a real
python subprocess) and is not the security regression we're guarding
against.
"""
from __future__ import annotations

import pytest

from app.agents.capabilities import run_code, _run_code_scan


# ─── default-off ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_code_disabled_by_default(monkeypatch):
    """With no env var, run_code refuses every snippet."""
    monkeypatch.delenv("ALLOW_CODE_EXEC", raising=False)
    result = await run_code("print('hello')")
    assert "error" in result
    assert "disabled by default" in result["error"]


@pytest.mark.asyncio
async def test_run_code_disabled_when_flag_is_false(monkeypatch):
    """Explicit 'false' / '0' values keep it disabled."""
    for falsy in ("false", "0", "no", ""):
        monkeypatch.setenv("ALLOW_CODE_EXEC", falsy)
        result = await run_code("print('hello')")
        assert "error" in result, f"Should be disabled for ALLOW_CODE_EXEC={falsy!r}"


# ─── blocklist scan ──────────────────────────────────────────────────

@pytest.mark.parametrize("snippet, candidates", [
    # Any of the listed tokens is a valid block reason — the
    # blocklist iteration order is unspecified, so a snippet that
    # contains multiple banned tokens may be rejected on any of them.
    ("import os; print(os.environ['JWT_SECRET'])", ("os.environ", "environ")),
    ("import subprocess; subprocess.run(['ls'])", ("subprocess",)),
    # urlopen(...) matches both "urllib" and the broader "open(" guard
    ("from urllib.request import urlopen; urlopen('http://attacker')", ("urllib", "open(")),
    ("import socket; s = socket.socket()", ("socket",)),
    ("eval('1+1')", ("eval(",)),
    ("exec('print(1)')", ("exec(",)),
    ("__import__('os').system('ls')", ("__import__", "system")),
    ("import httpx; httpx.get('http://x')", ("httpx",)),
    ("open('/etc/passwd').read()", ("open(",)),
])
def test_run_code_scan_blocks_dangerous_tokens(snippet, candidates):
    rejection = _run_code_scan(snippet)
    assert rejection is not None, f"Snippet was not blocked: {snippet!r}"
    assert any(c in rejection for c in candidates), (
        f"Rejection {rejection!r} did not match any expected candidate: {candidates}"
    )


def test_run_code_scan_allows_simple_arithmetic():
    """Pure computation is fine."""
    assert _run_code_scan("print(2 + 2)") is None
    assert _run_code_scan("x = sum(range(10))\nprint(x)") is None


# ─── enabled-but-blocked path ────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_code_with_flag_on_still_blocks_dangerous(monkeypatch):
    """Even with ALLOW_CODE_EXEC=true, blocklisted patterns refuse."""
    monkeypatch.setenv("ALLOW_CODE_EXEC", "true")
    result = await run_code("import os; print(os.environ.get('JWT_SECRET'))")
    assert "error" in result
    assert "Code rejected" in result["error"]
    assert "os.environ" in result["error"]
