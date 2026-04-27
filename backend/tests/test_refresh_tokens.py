"""Tests for the H-2 Phase 3 refresh-token storage layer.

Uses an in-memory fake Redis client to exercise the real code paths
without requiring a live Redis. The fake supports the subset of
commands `app.auth.refresh` calls: get/set/delete/sadd/smembers/srem
/expire/incr.

Coverage:
- issue + consume happy path (single-use semantics)
- consume of an unknown / already-consumed token returns None
- revoke_refresh_token deletes the token and removes it from the
  user-set
- revoke_all_for_user removes every token tied to a user
- Redis unavailability returns None / False without raising
- Token rotation: each consume returns claims, every consume after
  the first hits None (single-use)
"""
from __future__ import annotations

import json

import pytest

from app.auth import refresh as refresh_mod


class _FakeRedis:
    """Minimal async Redis stand-in for the refresh module's needs."""

    def __init__(self):
        self.kv: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}

    async def set(self, key, value, ex=None):
        self.kv[key] = value

    async def get(self, key):
        return self.kv.get(key)

    async def delete(self, *keys):
        deleted = 0
        for k in keys:
            if k in self.kv:
                del self.kv[k]
                deleted += 1
            if k in self.sets:
                del self.sets[k]
                deleted += 1
        return deleted

    async def sadd(self, key, *members):
        s = self.sets.setdefault(key, set())
        s.update(members)
        return len(members)

    async def smembers(self, key):
        return set(self.sets.get(key, set()))

    async def srem(self, key, *members):
        if key not in self.sets:
            return 0
        before = len(self.sets[key])
        self.sets[key] -= set(members)
        return before - len(self.sets[key])

    async def expire(self, key, ttl):
        # Fake — no-op for unit testing.
        return True


@pytest.fixture
def fake_redis(monkeypatch):
    """Inject a fresh fake Redis for each test."""
    fake = _FakeRedis()

    async def _redis_stub():
        return fake

    monkeypatch.setattr(refresh_mod, "_redis", _redis_stub)
    return fake


# ─── happy path ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_issue_and_consume_returns_claims(fake_redis):
    token = await refresh_mod.issue_refresh_token("user-1", "a@b.com", "member")
    assert isinstance(token, str) and len(token) > 20

    claims = await refresh_mod.consume_refresh_token(token)
    assert claims is not None
    assert claims["user_id"] == "user-1"
    assert claims["email"] == "a@b.com"
    assert claims["role"] == "member"


@pytest.mark.asyncio
async def test_consume_is_single_use(fake_redis):
    """Rotation policy: each refresh token works exactly once."""
    token = await refresh_mod.issue_refresh_token("user-1", "a@b.com", "member")
    first = await refresh_mod.consume_refresh_token(token)
    assert first is not None

    second = await refresh_mod.consume_refresh_token(token)
    assert second is None  # already consumed


# ─── error paths ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consume_unknown_token_returns_none(fake_redis):
    assert await refresh_mod.consume_refresh_token("not-a-real-token") is None


@pytest.mark.asyncio
async def test_consume_empty_returns_none(fake_redis):
    assert await refresh_mod.consume_refresh_token("") is None
    assert await refresh_mod.consume_refresh_token(None) is None


@pytest.mark.asyncio
async def test_issue_returns_none_when_redis_down(monkeypatch):
    async def _no_redis():
        return None
    monkeypatch.setattr(refresh_mod, "_redis", _no_redis)
    result = await refresh_mod.issue_refresh_token("user-1", "a@b.com")
    assert result is None


# ─── revocation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_revoke_refresh_token(fake_redis):
    token = await refresh_mod.issue_refresh_token("user-1", "a@b.com", "member")
    ok = await refresh_mod.revoke_refresh_token(token)
    assert ok is True
    # After revoke, consume returns None.
    assert await refresh_mod.consume_refresh_token(token) is None


@pytest.mark.asyncio
async def test_revoke_all_for_user(fake_redis):
    """Issue 3 tokens for one user + 1 for another, revoke_all the
    first user, verify only their 3 are gone."""
    t1 = await refresh_mod.issue_refresh_token("user-A", "a@b.com")
    t2 = await refresh_mod.issue_refresh_token("user-A", "a@b.com")
    t3 = await refresh_mod.issue_refresh_token("user-A", "a@b.com")
    other = await refresh_mod.issue_refresh_token("user-B", "b@b.com")

    n = await refresh_mod.revoke_all_for_user("user-A")
    assert n == 3

    assert await refresh_mod.consume_refresh_token(t1) is None
    assert await refresh_mod.consume_refresh_token(t2) is None
    assert await refresh_mod.consume_refresh_token(t3) is None
    # user-B's token is untouched.
    other_claims = await refresh_mod.consume_refresh_token(other)
    assert other_claims is not None
    assert other_claims["user_id"] == "user-B"


@pytest.mark.asyncio
async def test_revoke_all_for_user_empty(fake_redis):
    """No tokens for a user → revoke_all returns 0, not error."""
    assert await refresh_mod.revoke_all_for_user("never-existed") == 0


# ─── token uniqueness ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_each_issued_token_is_unique(fake_redis):
    tokens = [
        await refresh_mod.issue_refresh_token("user-1", "a@b.com")
        for _ in range(10)
    ]
    assert len(set(tokens)) == 10  # no collisions


@pytest.mark.asyncio
async def test_token_hash_used_as_key(fake_redis):
    """Refresh tokens themselves should NEVER appear in Redis — only
    their sha256 hashes."""
    token = await refresh_mod.issue_refresh_token("user-1", "a@b.com")
    # The plain token must not be a Redis key.
    assert not any(token in k for k in fake_redis.kv.keys())
    # But the token-hash key MUST be there.
    expected_key = f"{refresh_mod._TOKEN_KEY_PREFIX}{refresh_mod._hash_token(token)}"
    assert expected_key in fake_redis.kv
