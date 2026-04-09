"""API Key management — generate, validate, revoke."""

import hashlib
import logging
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .jwt_handler import verify_token
from ..db.client import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-keys", tags=["API Keys"])

KEY_PREFIX = "nf_"


def _generate_key() -> tuple[str, str]:
    """Generate API key and its hash. Returns (raw_key, hash)."""
    raw = KEY_PREFIX + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def validate_api_key(raw_key: str) -> Optional[dict]:
    """Validate API key and return user info. Returns None if invalid."""
    key_hash = _hash_key(raw_key)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT ak.*, u.email, u.name, u.role, u.plan
                   FROM api_keys ak JOIN nf_users u ON ak.user_id = u.id
                   WHERE ak.key_hash = $1 AND ak.is_active = true""",
                key_hash,
            )
            if not row:
                return None

            # Update last used
            await conn.execute(
                "UPDATE api_keys SET last_used_at = now(), requests_today = requests_today + 1 WHERE id = $1",
                row["id"],
            )

            return {
                "user_id": str(row["user_id"]),
                "email": row["email"],
                "name": row["name"],
                "role": row["role"],
                "plan": row["plan"],
                "scopes": row["scopes"],
                "key_name": row["name"],
            }
    except Exception as e:
        logger.warning("API key validation error: %s", e)
        return None


class CreateKeyRequest(BaseModel):
    name: str = "Default"


@router.post("/generate")
async def generate_key(req: CreateKeyRequest, request: Request):
    """Generate a new API key for the authenticated user."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    raw_key, key_hash = _generate_key()
    prefix = raw_key[:12]

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Limit: max 5 keys per user
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM api_keys WHERE user_id = $1::uuid AND is_active = true",
            token_data["sub"],
        )
        if count >= 5:
            raise HTTPException(400, "Maximum 5 active API keys per account")

        await conn.execute(
            """INSERT INTO api_keys (user_id, key_hash, key_prefix, name)
               VALUES ($1::uuid, $2, $3, $4)""",
            token_data["sub"], key_hash, prefix, req.name,
        )

    logger.info("API key generated: %s (user %s)", prefix, token_data["sub"][:8])

    # Return raw key ONLY on creation — never stored in plain text
    return {
        "key": raw_key,
        "prefix": prefix,
        "name": req.name,
        "message": "Save this key — it won't be shown again.",
    }


@router.get("/")
async def list_keys(request: Request):
    """List active API keys (prefix only, not full key)."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, key_prefix, name, scopes, last_used_at, requests_today, created_at
               FROM api_keys WHERE user_id = $1::uuid AND is_active = true
               ORDER BY created_at DESC""",
            token_data["sub"],
        )

    return {
        "keys": [{
            "id": str(r["id"]),
            "prefix": r["key_prefix"],
            "name": r["name"],
            "scopes": r["scopes"],
            "last_used": r["last_used_at"].isoformat() if r["last_used_at"] else None,
            "requests_today": r["requests_today"],
            "created_at": r["created_at"].isoformat(),
        } for r in rows]
    }


@router.delete("/{key_id}")
async def revoke_key(key_id: str, request: Request):
    """Revoke an API key."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE api_keys SET is_active = false WHERE id = $1::uuid AND user_id = $2::uuid",
            key_id, token_data["sub"],
        )

    return {"revoked": True}
