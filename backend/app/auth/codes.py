"""Auth code management — stored in PostgreSQL, shared across workers.

L-4 (2026-04-25): added per-(email, purpose) failure counter on
`verify_code` to block brute-forcing of the 6-digit code. With 900k
possible codes, a bot at 100 req/s clears all of them in 2.5 hours.
The counter caps at 5 failed verifies per (email, purpose) per
TTL window; subsequent attempts return False without consulting
PostgreSQL. Fail-open on Redis errors (don't lock everyone out).
"""

import secrets
import logging
from datetime import datetime, timedelta, timezone

from app.db.client import get_db_pool

logger = logging.getLogger(__name__)

TTL_MINUTES = 15

# L-4: brute-force lockout threshold + window.
_VERIFY_FAIL_LIMIT = 5
_VERIFY_FAIL_WINDOW_SECONDS = TTL_MINUTES * 60


async def create_code(email: str, purpose: str) -> str:
    """Generate a 6-digit code, store in DB, return it. Replaces any existing code for this email+purpose."""
    code = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=TTL_MINUTES)

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Delete old codes for this email+purpose
            await conn.execute(
                "DELETE FROM auth_codes WHERE email = $1 AND purpose = $2",
                email, purpose,
            )
            # Insert new code
            await conn.execute(
                "INSERT INTO auth_codes (email, code, purpose, expires_at) VALUES ($1, $2, $3, $4)",
                email, code, purpose, expires_at,
            )
            # Cleanup expired codes (best-effort)
            await conn.execute(
                "DELETE FROM auth_codes WHERE expires_at < NOW() - INTERVAL '1 hour'"
            )
    except Exception as exc:
        logger.warning("Failed to store auth code in DB: %s", exc)
        # Fallback: return code anyway (it won't be verifiable, but email will still be sent)

    return code


async def _check_verify_lockout(email: str, purpose: str) -> bool:
    """L-4: returns True if this (email, purpose) is currently locked
    out from verifying. Fail-open on Redis errors."""
    try:
        from app.db.client import get_redis
        r = await get_redis()
        if r is None:
            return False
        key = f"nf:auth_code_fail:{purpose}:{email.lower()}"
        count = await r.get(key)
        return count is not None and int(count) >= _VERIFY_FAIL_LIMIT
    except Exception:
        return False


async def _record_verify_failure(email: str, purpose: str) -> None:
    """L-4: bump the per-(email, purpose) failure counter."""
    try:
        from app.db.client import get_redis
        r = await get_redis()
        if r is None:
            return
        key = f"nf:auth_code_fail:{purpose}:{email.lower()}"
        n = await r.incr(key)
        if n == 1:
            await r.expire(key, _VERIFY_FAIL_WINDOW_SECONDS)
    except Exception:
        # Don't break verify on Redis blip.
        return


async def verify_code(email: str, purpose: str, code: str) -> bool:
    """Check if the code is valid. Returns True and marks as used, or False."""
    # L-4: short-circuit if locked out.
    if await _check_verify_lockout(email, purpose):
        logger.warning("auth_code lockout: %s/%s exceeded %d fails", purpose, email[:6], _VERIFY_FAIL_LIMIT)
        return False

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, code, expires_at, used FROM auth_codes
                   WHERE email = $1 AND purpose = $2 AND used = false
                   ORDER BY created_at DESC LIMIT 1""",
                email, purpose,
            )
            if not row:
                await _record_verify_failure(email, purpose)
                return False
            if row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                # Expired — delete and return false
                await conn.execute("DELETE FROM auth_codes WHERE id = $1", row["id"])
                await _record_verify_failure(email, purpose)
                return False
            if row["code"] != code:
                await _record_verify_failure(email, purpose)
                return False
            # Mark as used
            await conn.execute("UPDATE auth_codes SET used = true WHERE id = $1", row["id"])
            return True
    except Exception as exc:
        logger.warning("Failed to verify auth code: %s", exc)
        return False
