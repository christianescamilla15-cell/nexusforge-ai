"""Tests for the MockProvider terminal-fallback graft (from CallForge)."""

import pytest

from app.llm.mock_provider import MockProvider


@pytest.mark.asyncio
async def test_mock_disabled_by_default(monkeypatch):
    """Without explicit opt-in, MockProvider is_available() must return False."""
    from app.llm import mock_provider as mod
    monkeypatch.setattr(mod.settings, "mock_llm_enabled", False, raising=False)
    p = MockProvider()
    assert p.is_available() is False


@pytest.mark.asyncio
async def test_mock_enabled_returns_deterministic(monkeypatch):
    """Same input → same response. Required for snapshot-style tests."""
    from app.llm import mock_provider as mod
    monkeypatch.setattr(mod.settings, "mock_llm_enabled", True, raising=False)
    p = MockProvider()
    assert p.is_available() is True

    messages = [{"role": "user", "content": "hello there"}]
    r1 = await p.chat(messages)
    r2 = await p.chat(messages)
    assert r1.text == r2.text
    assert r1.provider == "mock"
    assert r1.cost_usd == 0.0
    assert r1.model == "mock-deterministic"


@pytest.mark.asyncio
async def test_mock_emits_json_when_requested(monkeypatch):
    """JSON-mode hint → mock returns valid JSON so downstream parsers don't break."""
    import json
    from app.llm import mock_provider as mod
    monkeypatch.setattr(mod.settings, "mock_llm_enabled", True, raising=False)
    p = MockProvider()
    r = await p.chat([{"role": "user", "content": "return as JSON please"}])
    parsed = json.loads(r.text)
    assert parsed["mock"] is True
    assert "echo_hash" in parsed
