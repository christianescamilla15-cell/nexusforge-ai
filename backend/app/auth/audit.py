"""Per-user activity log with token / cost attribution.

Despite the historical "audit" naming, this module is NOT the
compliance audit trail — that lives in `app/routes/audit.py` and
writes to the `audit_logs` (plural) table with entity_type /
entity_id / changes columns. This module writes to `audit_log`
(singular) and serves as a per-user activity feed showing tokens
consumed, dollar cost, and duration per action.

The two systems share the unfortunate `/audit` prefix history:
both modules used to mount at `/api/audit/`, with this one
registering first and silently shadowing the compliance audit
routes (a 404 / 500 from the SQL bug at line 67 is what users
saw on the audit page in production). The 2026-04-30 fix moved
this module's HTTP surface to `/api/activity/` so the two no
longer collide. The `log_action()` helper signature is unchanged;
existing callers in `custom_agents.py` keep working.
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from .jwt_handler import verify_token
from ..db.client import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/activity", tags=["Activity Log"])


async def log_action(
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    tokens_used: int = 0,
    cost_usd: float = 0.0,
    duration_ms: int = 0,
) -> None:
    """Log an action to the audit trail. Non-fatal."""
    try:
        pool = await get_db_pool()
        if not pool:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO audit_log (user_id, action, resource_type, resource_id,
                   details, ip_address, tokens_used, cost_usd, duration_ms)
                   VALUES ($1::uuid, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)""",
                user_id, action, resource_type, resource_id,
                json.dumps(details or {}), ip_address, tokens_used, cost_usd, duration_ms,
            )
    except Exception as e:
        logger.warning("Audit log failed: %s", e)


@router.get("/")
async def get_audit_log(request: Request, limit: int = 50, action: Optional[str] = None):
    """Get audit trail for the authenticated user."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if action:
            rows = await conn.fetch(
                """SELECT id, action, resource_type, resource_id, details,
                          tokens_used, cost_usd, duration_ms, created_at
                   FROM audit_log WHERE user_id = $1::uuid AND action = $2
                   ORDER BY created_at DESC LIMIT $3""",
                token_data["sub"], action, limit,
            )
        else:
            rows = await conn.fetch(
                """SELECT id, action, resource_type, resource_id, details,
                          tokens_used, cost_usd, duration_ms, created_at
                   FROM audit_log WHERE user_id = $1::uuid
                   ORDER BY created_at DESC LIMIT $2""",
                token_data["sub"], limit,
            )

    return {
        "entries": [{
            "id": str(r["id"]),
            "action": r["action"],
            "resource_type": r["resource_type"],
            "resource_id": r["resource_id"],
            "details": r["details"],
            "tokens": r["tokens_used"],
            "cost": float(r["cost_usd"]),
            "duration_ms": r["duration_ms"],
            "at": r["created_at"].isoformat(),
        } for r in rows],
        "total": len(rows),
    }


@router.get("/summary")
async def get_audit_summary(request: Request):
    """Get usage summary for the authenticated user."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        stats = await conn.fetchrow(
            """SELECT
                COUNT(*) as total_actions,
                COALESCE(SUM(tokens_used), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0) as total_cost,
                COUNT(DISTINCT DATE(created_at)) as active_days
               FROM audit_log WHERE user_id = $1::uuid""",
            token_data["sub"],
        )

    return {
        "total_actions": stats["total_actions"],
        "total_tokens": int(stats["total_tokens"]),
        "total_cost": float(stats["total_cost"]),
        "active_days": stats["active_days"],
    }
