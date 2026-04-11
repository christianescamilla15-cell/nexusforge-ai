"""Tests for Phase 4 — Agent SDK subagent memory.

Covers the pieces of ``app.meta.agent_sdk_bridge`` that can be
exercised without a real ``claude_agent_sdk`` install:

- ``_load_session`` / ``_save_session`` Redis persistence helpers,
  including the graceful no-op path when Redis is unavailable.
- ``resume`` wrapper — when the SDK is not available, it must return
  the unavailable sentinel dict without raising.
- ``run`` with ``user_id`` — when the SDK is not available, the
  unavailable path must NOT attempt to touch Redis.
- The Redis key format is stable (``nexusforge:sdk:session:{user_id}:{agent_name}``)
  so external tooling can inspect it.

The real SDK execution path (``_execute`` → ``query(...)``) requires
``claude-agent-sdk`` + an Anthropic API key and is covered by
end-to-end tests, not these unit tests.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.meta.agent_sdk_bridge import (
    _SESSION_REDIS_KEY,
    _SESSION_TTL_SECONDS,
    AgentSDKBridge,
)


# ── Redis key format ───────────────────────────────────────────────────


def test_session_redis_key_format_is_stable():
    """The key template is part of the public contract with ops /
    observability tooling. If this changes, update docs/DEPLOYMENT.md
    section 'Render ephemeral filesystem caveat' in the same commit."""
    assert _SESSION_REDIS_KEY == "nexusforge:sdk:session:{user_id}:{agent_name}"
    rendered = _SESSION_REDIS_KEY.format(user_id="u42", agent_name="security-auditor")
    assert rendered == "nexusforge:sdk:session:u42:security-auditor"


def test_session_ttl_is_at_least_one_week():
    """The TTL must outlast a typical Render redeploy cadence so
    session ids are not pruned during a normal workday."""
    assert _SESSION_TTL_SECONDS >= 7 * 24 * 3600


# ── _save_session / _load_session happy path ──────────────────────────


@pytest.mark.asyncio
async def test_save_session_writes_with_ttl():
    bridge = AgentSDKBridge()

    fake_redis = AsyncMock()
    fake_redis.set = AsyncMock()

    with patch("app.db.client.get_redis", new=AsyncMock(return_value=fake_redis)):
        await bridge._save_session("user42", "security-auditor", "sess-abc-123")

    fake_redis.set.assert_awaited_once()
    args, kwargs = fake_redis.set.call_args
    # Key name
    assert args[0] == "nexusforge:sdk:session:user42:security-auditor"
    # Value
    assert args[1] == "sess-abc-123"
    # TTL passed as `ex=`
    assert kwargs.get("ex") == _SESSION_TTL_SECONDS


@pytest.mark.asyncio
async def test_load_session_returns_stored_value_as_str():
    bridge = AgentSDKBridge()

    fake_redis = AsyncMock()
    fake_redis.get = AsyncMock(return_value=b"sess-abc-123")

    with patch("app.db.client.get_redis", new=AsyncMock(return_value=fake_redis)):
        got = await bridge._load_session("user42", "security-auditor")

    assert got == "sess-abc-123"
    fake_redis.get.assert_awaited_once_with(
        "nexusforge:sdk:session:user42:security-auditor"
    )


@pytest.mark.asyncio
async def test_load_session_returns_none_when_key_missing():
    bridge = AgentSDKBridge()

    fake_redis = AsyncMock()
    fake_redis.get = AsyncMock(return_value=None)

    with patch("app.db.client.get_redis", new=AsyncMock(return_value=fake_redis)):
        got = await bridge._load_session("user42", "security-auditor")

    assert got is None


# ── Graceful degradation paths ────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_session_returns_none_when_redis_unavailable():
    """If get_redis returns None (Redis config missing), _load_session
    must silently return None rather than raise."""
    bridge = AgentSDKBridge()

    with patch("app.db.client.get_redis", new=AsyncMock(return_value=None)):
        got = await bridge._load_session("user42", "architect")

    assert got is None


@pytest.mark.asyncio
async def test_save_session_swallows_redis_errors():
    """Redis I/O errors must never propagate out of _save_session —
    session persistence is best-effort and must not break run()."""
    bridge = AgentSDKBridge()

    fake_redis = AsyncMock()
    fake_redis.set = AsyncMock(side_effect=RuntimeError("connection refused"))

    with patch("app.db.client.get_redis", new=AsyncMock(return_value=fake_redis)):
        # Must not raise
        await bridge._save_session("user42", "architect", "sess-xyz")


@pytest.mark.asyncio
async def test_load_session_swallows_redis_errors():
    """Same contract as _save_session: errors must be swallowed."""
    bridge = AgentSDKBridge()

    fake_redis = AsyncMock()
    fake_redis.get = AsyncMock(side_effect=RuntimeError("connection refused"))

    with patch("app.db.client.get_redis", new=AsyncMock(return_value=fake_redis)):
        got = await bridge._load_session("user42", "architect")

    assert got is None


# ── run() and resume() unavailable path ──────────────────────────────


@pytest.mark.asyncio
async def test_run_unavailable_returns_sentinel_without_touching_redis():
    """When the bridge is not available (no SDK / no API key), run()
    must short-circuit before any Redis I/O — even when user_id is
    passed. Otherwise an unrelated Redis outage would turn into a
    confusing 'unavailable' bug."""
    bridge = AgentSDKBridge()
    # Force unavailable regardless of local env
    bridge._available = False

    fake_redis = AsyncMock()
    fake_redis.get = AsyncMock()
    fake_redis.set = AsyncMock()

    with patch("app.db.client.get_redis", new=AsyncMock(return_value=fake_redis)):
        result = await bridge.run(
            prompt="hello",
            user_id="user42",
            agent_name="architect",
            resume_session=True,
        )

    assert result["status"] == "unavailable"
    # Redis must not have been touched on the unavailable path
    fake_redis.get.assert_not_awaited()
    fake_redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_resume_delegates_to_run_with_resume_true():
    """resume() is a thin wrapper. Verify it sets resume_session=True
    and forwards user_id + agent_name correctly."""
    bridge = AgentSDKBridge()

    captured: dict = {}

    async def fake_run(**kwargs):
        captured.update(kwargs)
        return {"status": "unavailable", "session_id": None}

    with patch.object(bridge, "run", new=fake_run):
        await bridge.resume(
            prompt="continue the audit",
            user_id="user42",
            agent_name="security-auditor",
        )

    assert captured["resume_session"] is True
    assert captured["user_id"] == "user42"
    assert captured["agent_name"] == "security-auditor"
    assert captured["prompt"] == "continue the audit"
