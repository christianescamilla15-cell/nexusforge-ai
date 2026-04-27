"""Refresh token storage + rotation — H-2 Phase 3 (2026-04-27).

Design
======

Two-token model (when `ENABLE_REFRESH_TOKENS=true`):

- **Access token**: short-lived JWT (15 minutes), stateless, carries
  user identity. Sent as `Authorization: Bearer <token>` on every
  API call. The existing JWT plumbing
  (`jwt_handler.create_token` + `verify_token`) handles it.

- **Refresh token**: opaque random string (32 bytes urlsafe-base64,
  43 chars), stored server-side in Redis with the user's claims,
  TTL = 7 days. Only ever sent to the `/api/auth/refresh` endpoint,
  never to any other route.

Rotation policy
---------------
Each successful `/auth/refresh` call issues a NEW refresh token AND
revokes the one used. This is "refresh token rotation" and limits
the blast radius of a stolen refresh token to one use.

Revocation
----------
- `revoke_refresh_token(token)` removes the single token (logout).
- `revoke_all_for_user(user_id)` removes every refresh token tied
  to a user (forced re-auth, account compromise response).
- TTL handles natural expiry — Redis evicts after 7 days.

Storage shape
-------------
Two Redis keys per token:

  nf:refresh:tok:<sha256(token)>         → JSON claims (TTL = 7d)
  nf:refresh:user:<user_id>              → SET of token hashes (for
                                            revoke_all_for_user); TTL
                                            extended on each issue.

Why hash the token before using it as a key? So a Redis dump does
not leak refresh tokens themselves — only their hashes are stored.
The plaintext token only ever lives in the user's HTTP response and
their client.

Fail behavior
-------------
If Redis is unavailable, refresh-token operations FAIL CLOSED — the
caller receives a 503 from the endpoint layer. Unlike JWT revocation
(H-2 partial, fail-open) this is the primary token issuance path
and a soft fail would create unexplained login failures in
production.
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from typing import Any

logger = logging.getLogger(__name__)

REFRESH_TTL_SECONDS = 7 * 24 * 3600  # 7 days
_TOKEN_KEY_PREFIX = "nf:refresh:tok:"
_USER_KEY_PREFIX = "nf:refresh:user:"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _redis():
    """Lazy redis client lookup; returns None if unavailable."""
    try:
        from app.db.client import get_redis
        return await get_redis()
    except Exception:
        return None


async def issue_refresh_token(
    user_id: str,
    email: str,
    role: str = "member",
) -> str | None:
    """Issue a new refresh token. Returns the opaque string, or None
    if Redis is unavailable.

    The caller (login flow) is responsible for returning this token
    in the HTTP response. Once returned, it cannot be retrieved
    again — only used / revoked.
    """
    r = await _redis()
    if r is None:
        logger.error("issue_refresh_token: Redis unavailable")
        return None
    if not user_id:
        return None
    token = secrets.token_urlsafe(32)
    h = _hash_token(token)
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "issued_at": int(time.time()),
    }
    try:
        await r.set(
            f"{_TOKEN_KEY_PREFIX}{h}",
            json.dumps(payload),
            ex=REFRESH_TTL_SECONDS,
        )
        # Track the token under the user's set so revoke_all can
        # iterate. SADD + EXPIRE is sufficient — TTL is reset to 7d
        # on each new issue.
        await r.sadd(f"{_USER_KEY_PREFIX}{user_id}", h)
        await r.expire(f"{_USER_KEY_PREFIX}{user_id}", REFRESH_TTL_SECONDS)
        return token
    except Exception:
        logger.exception("issue_refresh_token: Redis write failed")
        return None


async def consume_refresh_token(token: str) -> dict[str, Any] | None:
    """Validate the refresh token, revoke it (rotation), and return
    the claims it carried. Returns None if the token is invalid /
    expired / Redis unavailable.

    Called by the `/auth/refresh` endpoint. The caller must then
    issue a NEW refresh token (via `issue_refresh_token`) so the
    user keeps a valid rotation chain.
    """
    if not token:
        return None
    r = await _redis()
    if r is None:
        return None
    h = _hash_token(token)
    key = f"{_TOKEN_KEY_PREFIX}{h}"
    try:
        raw = await r.get(key)
        if not raw:
            return None
        # Single-use semantics: delete the token immediately so a
        # replay (legitimate or attacker) hits an empty key. The
        # caller has the claims and will mint a new token.
        await r.delete(key)
        claims = json.loads(raw)
        # Best-effort cleanup of the user-set entry.
        try:
            await r.srem(f"{_USER_KEY_PREFIX}{claims.get('user_id')}", h)
        except Exception:
            pass
        return claims
    except Exception:
        logger.exception("consume_refresh_token: Redis op failed")
        return None


async def revoke_refresh_token(token: str) -> bool:
    """Delete a single refresh token (logout flow)."""
    if not token:
        return False
    r = await _redis()
    if r is None:
        return False
    h = _hash_token(token)
    try:
        # Look up user_id first so we can clean the set entry.
        raw = await r.get(f"{_TOKEN_KEY_PREFIX}{h}")
        await r.delete(f"{_TOKEN_KEY_PREFIX}{h}")
        if raw:
            try:
                claims = json.loads(raw)
                user_id = claims.get("user_id")
                if user_id:
                    await r.srem(f"{_USER_KEY_PREFIX}{user_id}", h)
            except Exception:
                pass
        return True
    except Exception:
        logger.exception("revoke_refresh_token: Redis op failed")
        return False


async def revoke_all_for_user(user_id: str) -> int:
    """Remove every refresh token for a user. Returns the count.

    Used for: account compromise response, password change, forced
    sign-out across all devices, plan downgrade, etc.
    """
    if not user_id:
        return 0
    r = await _redis()
    if r is None:
        return 0
    user_key = f"{_USER_KEY_PREFIX}{user_id}"
    try:
        hashes = await r.smembers(user_key)
        if not hashes:
            return 0
        deleted = 0
        for h in hashes:
            try:
                # Redis returns bytes for set members in some clients;
                # decode if needed.
                h_str = h.decode() if isinstance(h, bytes) else h
                if await r.delete(f"{_TOKEN_KEY_PREFIX}{h_str}"):
                    deleted += 1
            except Exception:
                continue
        await r.delete(user_key)
        return deleted
    except Exception:
        logger.exception("revoke_all_for_user: Redis op failed")
        return 0
