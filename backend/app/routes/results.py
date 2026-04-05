"""Automation Results — persistent storage for automation outputs."""

import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.db.client import get_db_pool

router = APIRouter(prefix="/results", tags=["results"])
logger = logging.getLogger(__name__)


def _get_user_id(request: Request) -> Optional[str]:
    """Extract user_id from JWT. Returns None for anonymous."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        data = verify_token(auth[7:])
        if data:
            return data.get("sub")
    return None


class SaveResultRequest(BaseModel):
    """Request to save an automation result."""
    automation_id: UUID
    run_id: Optional[UUID] = None
    input_type: str = "text"
    input_data: dict = {}
    output_data: dict = {}
    status: str = "completed"
    processing_time_ms: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0


@router.get("/automation/{automation_id}")
async def list_results(
    automation_id: UUID,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List results for an automation, filtered by user."""
    user_id = _get_user_id(request)
    if not user_id:
        return {"items": [], "total": 0}

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify ownership
            auto = await conn.fetchrow(
                "SELECT id FROM automations WHERE id = $1 AND user_id = $2::uuid",
                automation_id, user_id,
            )
            if not auto:
                raise HTTPException(404, "Automation not found")

            total = await conn.fetchval(
                "SELECT count(*) FROM automation_results WHERE automation_id = $1",
                automation_id,
            )
            rows = await conn.fetch(
                """SELECT id, input_type, input_data, output_data, status,
                          processing_time_ms, tokens_used, cost_usd, run_id, created_at
                   FROM automation_results
                   WHERE automation_id = $1
                   ORDER BY created_at DESC
                   LIMIT $2 OFFSET $3""",
                automation_id, limit, offset,
            )

        items = []
        for r in rows:
            inp = r["input_data"]
            if isinstance(inp, str):
                inp = json.loads(inp)
            out = r["output_data"]
            if isinstance(out, str):
                out = json.loads(out)
            items.append({
                "id": str(r["id"]),
                "input_type": r["input_type"],
                "input_data": inp,
                "output_data": out,
                "status": r["status"],
                "processing_time_ms": r["processing_time_ms"],
                "tokens_used": r["tokens_used"],
                "cost_usd": float(r["cost_usd"] or 0),
                "run_id": str(r["run_id"]) if r["run_id"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            })

        return {"items": items, "total": total or 0, "limit": limit, "offset": offset}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list results")
        raise HTTPException(500, str(exc))


@router.get("/pending-approvals")
async def list_pending_approvals(request: Request):
    """List all results pending approval for the current user."""
    user_id = _get_user_id(request)
    if not user_id:
        return {"items": [], "total": 0}

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT ar.id, ar.automation_id, ar.input_data, ar.output_data,
                          ar.processing_time_ms, ar.created_at, a.name AS automation_name,
                          a.icon AS automation_icon
                   FROM automation_results ar
                   JOIN automations a ON a.id = ar.automation_id
                   WHERE a.user_id = $1::uuid AND ar.approval_status = 'pending'
                   ORDER BY ar.created_at DESC
                   LIMIT 50""",
                user_id,
            )
        items = []
        for r in rows:
            inp = r["input_data"]
            if isinstance(inp, str):
                inp = json.loads(inp)
            out = r["output_data"]
            if isinstance(out, str):
                out = json.loads(out)
            items.append({
                "id": str(r["id"]),
                "automation_id": str(r["automation_id"]),
                "automation_name": r["automation_name"],
                "automation_icon": r["automation_icon"],
                "input_data": inp,
                "output_data": out,
                "processing_time_ms": r["processing_time_ms"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            })
        return {"items": items, "total": len(items)}
    except Exception as exc:
        logger.exception("Failed to list pending approvals")
        raise HTTPException(500, str(exc))


@router.get("/{result_id}")
async def get_result(result_id: UUID, request: Request):
    """Get a single result by ID."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM automation_results WHERE id = $1", result_id,
            )
            if not row:
                raise HTTPException(404, "Result not found")

            # Verify user owns the automation
            if user_id:
                auto = await conn.fetchrow(
                    "SELECT user_id FROM automations WHERE id = $1",
                    row["automation_id"],
                )
                if auto and str(auto["user_id"]) != user_id:
                    raise HTTPException(403, "Access denied")

        inp = row["input_data"]
        if isinstance(inp, str):
            inp = json.loads(inp)
        out = row["output_data"]
        if isinstance(out, str):
            out = json.loads(out)

        return {
            "id": str(row["id"]),
            "automation_id": str(row["automation_id"]),
            "input_type": row["input_type"],
            "input_data": inp,
            "output_data": out,
            "status": row["status"],
            "processing_time_ms": row["processing_time_ms"],
            "tokens_used": row["tokens_used"],
            "cost_usd": float(row["cost_usd"] or 0),
            "run_id": str(row["run_id"]) if row["run_id"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get result")
        raise HTTPException(500, str(exc))


@router.post("/", status_code=201)
async def save_result(body: SaveResultRequest, request: Request):
    """Save a result from an automation execution."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(401, "Login required")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO automation_results
                       (automation_id, user_id, run_id, input_type, input_data,
                        output_data, status, processing_time_ms, tokens_used, cost_usd)
                   VALUES ($1, $2::uuid, $3, $4, $5::jsonb, $6::jsonb, $7, $8, $9, $10)
                   RETURNING id, created_at""",
                body.automation_id, user_id, body.run_id, body.input_type,
                json.dumps(body.input_data), json.dumps(body.output_data),
                body.status, body.processing_time_ms, body.tokens_used, body.cost_usd,
            )
        return {"id": str(row["id"]), "created_at": row["created_at"].isoformat()}
    except Exception as exc:
        logger.exception("Failed to save result")
        raise HTTPException(500, str(exc))


class ApprovalRequest(BaseModel):
    """Request to approve or reject a result."""
    action: str  # "approved" or "rejected"


@router.post("/{result_id}/approval")
async def approve_or_reject_result(result_id: UUID, body: ApprovalRequest, request: Request):
    """Approve or reject a pending result (human-in-the-loop)."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(401, "Login required")

    if body.action not in ("approved", "rejected"):
        raise HTTPException(400, "Action must be 'approved' or 'rejected'")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify ownership via automation
            row = await conn.fetchrow(
                """SELECT ar.id, ar.approval_status FROM automation_results ar
                   JOIN automations a ON a.id = ar.automation_id
                   WHERE ar.id = $1 AND a.user_id = $2::uuid""",
                result_id, user_id,
            )
            if not row:
                raise HTTPException(404, "Result not found")
            if row["approval_status"] != "pending":
                raise HTTPException(400, f"Result is not pending approval (current: {row['approval_status']})")

            await conn.execute(
                "UPDATE automation_results SET approval_status = $1 WHERE id = $2",
                body.action, result_id,
            )
        return {"id": str(result_id), "approval_status": body.action}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update approval status")
        raise HTTPException(500, str(exc))


@router.delete("/automation/{automation_id}/all")
async def delete_all_results(automation_id: UUID, request: Request):
    """Delete all results for an automation."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(401, "Login required")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                "SELECT id FROM automations WHERE id = $1 AND user_id = $2::uuid",
                automation_id, user_id,
            )
            if not auto:
                raise HTTPException(404, "Automation not found")

            count = await conn.fetchval(
                "DELETE FROM automation_results WHERE automation_id = $1 RETURNING count(*)",
                automation_id,
            )
        return {"deleted": True, "count": count or 0}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete all results")
        raise HTTPException(500, str(exc))


@router.delete("/{result_id}")
async def delete_result(result_id: UUID, request: Request):
    """Delete a result."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(401, "Login required")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify ownership via automation
            row = await conn.fetchrow(
                """SELECT ar.id FROM automation_results ar
                   JOIN automations a ON a.id = ar.automation_id
                   WHERE ar.id = $1 AND a.user_id = $2::uuid""",
                result_id, user_id,
            )
            if not row:
                raise HTTPException(404, "Result not found")

            await conn.execute(
                "DELETE FROM automation_results WHERE id = $1", result_id,
            )
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete result")
        raise HTTPException(500, str(exc))
