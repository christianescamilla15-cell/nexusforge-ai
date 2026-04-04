"""FastAPI dependency-injection helpers for auth + ownership checks."""

import logging
from fastapi import HTTPException, Request
from app.auth.jwt_handler import verify_token
from app.db.client import get_db_pool

logger = logging.getLogger(__name__)


def get_current_user_id(request: Request) -> str:
    """Extract and validate user_id from JWT. Raises 401 if missing/invalid."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    data = verify_token(auth[7:])
    if not data or not data.get("sub"):
        raise HTTPException(401, "Invalid or expired token")
    return data["sub"]


async def verify_automation_owner(automation_id: str, request: Request) -> str:
    """Verify the current user owns the automation. Returns user_id."""
    user_id = get_current_user_id(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM automations WHERE id = $1::uuid",
            automation_id,
        )
    if not row:
        raise HTTPException(404, "Automation not found")
    if str(row["user_id"]) != user_id:
        raise HTTPException(403, "You don't own this automation")
    return user_id


async def verify_workflow_owner(workflow_id: str, request: Request) -> str:
    """Verify the current user owns the workflow. Returns user_id."""
    user_id = get_current_user_id(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM workflows WHERE id = $1::uuid",
            workflow_id,
        )
    if not row:
        raise HTTPException(404, "Workflow not found")
    # user_id may be null for legacy workflows — allow
    if row["user_id"] and str(row["user_id"]) != user_id:
        raise HTTPException(403, "You don't own this workflow")
    return user_id
