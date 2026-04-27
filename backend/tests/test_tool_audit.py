"""Tests for the A-05 agent-tool egress audit decorator.

Verifies the audit DOES emit metadata-only events (no plaintext
content) and that wrapping a tool with `@audited` is transparent
to the caller (return value unchanged).
"""
from __future__ import annotations

import logging

import pytest

from app.agents.tool_audit import audited, _summarize_arg, _summarize_result


# ─── arg summarization (no content leaks) ─────────────────────────────

def test_summarize_arg_path_records_basename_only():
    out = _summarize_arg("path", "/etc/passwd")
    assert out["type"] == "path"
    assert out["basename"] == "passwd"
    # No directory component leaks into the summary.
    assert "/etc" not in str(out)


def test_summarize_arg_url_records_host_and_path_hash():
    out = _summarize_arg("url", "https://example.com/sensitive/path?token=abc")
    assert out["type"] == "url"
    assert out["host"] == "example.com"
    # The path+query is hashed, not stored.
    assert "sensitive" not in str(out)
    assert "token=abc" not in str(out)
    assert len(out["path_hash"]) == 12


def test_summarize_arg_code_records_length_only():
    out = _summarize_arg("code", "import os; print(os.environ['JWT_SECRET'])")
    assert out["type"] == "code"
    assert out["len"] > 0
    # Snippet body never leaks.
    assert "JWT_SECRET" not in str(out)
    assert "os.environ" not in str(out)


def test_summarize_arg_content_records_length_only():
    out = _summarize_arg("content", "secret payload data")
    assert out["type"] == "content"
    assert "secret payload" not in str(out)


def test_summarize_arg_generic_string_redacts():
    """Generic strings (non-special-named) only carry length."""
    out = _summarize_arg("query", "this is a sensitive search query")
    assert out["type"] == "str"
    assert "sensitive" not in str(out)


# ─── result summarization (no content leaks) ─────────────────────────

def test_summarize_result_dict_keys_only():
    result = {
        "stdout": "leaked stdout content",
        "stderr": "leaked stderr",
        "exit_code": 0,
    }
    out = _summarize_result(result)
    assert out["exit_code"] == 0
    assert out["stdout_len"] > 0
    assert "leaked" not in str(out)


def test_summarize_result_error_truncated():
    result = {"error": "x" * 500}
    out = _summarize_result(result)
    assert "error" in out
    assert len(out["error"]) <= 80


def test_summarize_result_content_field_redacted():
    result = {"content": "scraped html with PII inside", "source": "httpx", "status": 200}
    out = _summarize_result(result)
    assert out["content_len"] > 0
    assert out["status"] == 200
    assert out["source"] == "httpx"
    assert "PII" not in str(out)


# ─── decorator transparency ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_audited_returns_wrapped_value_unchanged():
    @audited("dummy")
    async def my_tool(x: int) -> dict:
        return {"doubled": x * 2}

    result = await my_tool(21)
    assert result == {"doubled": 42}


@pytest.mark.asyncio
async def test_audited_emits_info_on_success(caplog):
    @audited("dummy")
    async def ok_tool(path: str) -> dict:
        return {"size": 1234}

    with caplog.at_level(logging.INFO, logger="nexusforge.tool_audit"):
        await ok_tool("/tmp/x.txt")

    assert any("tool_audit" in m for m in caplog.messages)
    assert any("dummy" in m for m in caplog.messages)


@pytest.mark.asyncio
async def test_audited_emits_warning_on_tool_error(caplog):
    @audited("dummy")
    async def bad_tool(path: str) -> dict:
        return {"error": "oops"}

    with caplog.at_level(logging.WARNING, logger="nexusforge.tool_audit"):
        await bad_tool("/tmp/x.txt")

    # An audit line at WARNING level was emitted.
    levels = [r.levelname for r in caplog.records if r.name == "nexusforge.tool_audit"]
    assert "WARNING" in levels


@pytest.mark.asyncio
async def test_audited_records_exception_class_only(caplog):
    """If the tool raises, the audit emits the exception type name —
    never the full traceback or message."""
    @audited("dummy")
    async def crashy_tool() -> dict:
        raise ValueError("very specific secret error message")

    with caplog.at_level(logging.WARNING, logger="nexusforge.tool_audit"):
        with pytest.raises(ValueError):
            await crashy_tool()

    audit_lines = [
        r.getMessage() for r in caplog.records
        if r.name == "nexusforge.tool_audit"
    ]
    assert audit_lines
    # The exception class name is OK to surface; the message is not.
    assert any("ValueError" in line for line in audit_lines)
    assert not any("very specific secret" in line for line in audit_lines)


# ─── integration: real tool wrappers don't break ─────────────────────

@pytest.mark.asyncio
async def test_real_read_file_audit_doesnt_leak_path(tmp_path, caplog):
    """Smoke test: the real read_file tool with @audited writes a
    log line that contains the basename but not the full path."""
    from app.agents.capabilities import read_file
    p = tmp_path / "secret-folder" / "private-file.txt"
    p.parent.mkdir(parents=True)
    p.write_text("body content")

    with caplog.at_level(logging.INFO, logger="nexusforge.tool_audit"):
        result = await read_file(str(p))

    assert "content" in result
    audit_msg = " ".join(
        r.getMessage() for r in caplog.records
        if r.name == "nexusforge.tool_audit"
    )
    # Basename appears.
    assert "private-file.txt" in audit_msg
    # Containing directory does NOT.
    assert "secret-folder" not in audit_msg
