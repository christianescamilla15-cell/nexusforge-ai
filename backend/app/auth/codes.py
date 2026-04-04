"""Auth code management — stored in PostgreSQL, shared across workers."""

import secrets
import logging
from datetime import datetime, timedelta, timezone

from app.db.client import get_db_pool

logger = logging.getLogger(__name__)

TTL_MINUTES = 15


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


async def verify_code(email: str, purpose: str, code: str) -> bool:
    """Check if the code is valid. Returns True and marks as used, or False."""
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
                return False
            if row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                # Expired — delete and return false
                await conn.execute("DELETE FROM auth_codes WHERE id = $1", row["id"])
                return False
            if row["code"] != code:
                return False
            # Mark as used
            await conn.execute("UPDATE auth_codes SET used = true WHERE id = $1", row["id"])
            return True
    except Exception as exc:
        logger.warning("Failed to verify auth code: %s", exc)
        return False
