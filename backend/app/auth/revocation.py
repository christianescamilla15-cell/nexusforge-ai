"""JWT revocation list — Redis-backed jti blocklist.

H-2 partial (2026-04-25): the full retro recommendation includes
splitting `JWT_SECRET` into 3 separate secrets (signing / Mythos
HMAC / Fernet) plus refresh tokens. That's a multi-day refactor
because rotating Fernet requires re-encrypting every stored API key.

This module ships the *immediate* win: a way to revoke a leaked or
suspicious JWT before its 8h expiry. Tokens carry a `jti` claim
(see jwt_handler.create_token); on logout (or admin action), the
jti is added to a Redis set with TTL = remaining token lifetime.
verify_token() then refuses any token whose jti is in the set.

If Redis is unreachable we **fail-open** — i.e. tokens are not
checked against the revocation list. This is intentional: forcing
fail-closed on Redis hiccups would log every user out under load.
The trade-off: a leaked token survives a Redis outage. Acceptable
because revocation is a defense-in-depth feature, not the primary
control.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

# Redis key namespace.
_REVOKE_KEY_PREFIX = "nf:jwt:revoked:"


async def _get_redis():
    """Lazy redis client lookup; returns None if Redis unavailable."""
    try:
        from app.db.client import get_redis
        return await get_redis()
    except Exception:
        return None


async def revoke_jti(jti: str, exp_unix: int) -> bool:
    """Add a jti to the revocation set with TTL until token's natural
    expiry. Returns True on successful write, False on Redis miss.
    """
    if not jti:
        return False
    ttl = max(int(exp_unix - time.time()), 1)
    r = await _get_redis()
    if r is None:
        logger.warning("revoke_jti: Redis unavailable, jti %s NOT revoked", jti[:12])
        return False
    try:
        await r.set(f"{_REVOKE_KEY_PREFIX}{jti}", "1", ex=ttl)
        return True
    except Exception:
        logger.exception("revoke_jti: Redis write failed")
        return False


async def is_jti_revoked(jti: str) -> bool:
    """Return True iff jti has been explicitly revoked.

    Fail-open on Redis errors (returns False) — see module docstring.
    """
    if not jti:
        return False
    r = await _get_redis()
    if r is None:
        return False
    try:
        val = await r.get(f"{_REVOKE_KEY_PREFIX}{jti}")
        return val is not None
    except Exception:
        # Don't take down auth on a Redis blip.
        return False
