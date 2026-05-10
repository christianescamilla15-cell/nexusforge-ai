"""Audit routes — browse and export audit logs."""

import csv
import io
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.auth.jwt_handler import verify_token
from app.db.client import get_db_pool

router = APIRouter(prefix="/audit", tags=["audit"])
logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    return uid


def _row_to_dict(r) -> dict:
    changes = r["changes"]
    if isinstance(changes, str):
        changes = json.loads(changes)
    return {
        "id": str(r["id"]),
        "user_id": str(r["user_id"]) if r["user_id"] else None,
        "entity_type": r["entity_type"],
        "entity_id": str(r["entity_id"]),
        "action": r["action"],
        "changes": changes,
        "ip_address": r["ip_address"],
        "created_at": r["created_at"].isoformat(),
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/")
async def list_audit(
    request: Request,
    entity_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List recent audit entries with optional entity_type filter (paginated)."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            conditions = ["user_id = $1::uuid"]
            params: list = [user_id]
            if entity_type:
                conditions.append(f"entity_type = ${len(params) + 1}")
                params.append(entity_type)

            where = "WHERE " + " AND ".join(conditions)
            idx = len(params)
            params.append(limit)
            params.append(offset)

            rows = await conn.fetch(
                f"""SELECT * FROM audit_logs
                    {where}
                    ORDER BY created_at DESC
                    LIMIT ${idx + 1} OFFSET ${idx + 2}""",
                *params,
            )

            # mythos: sqli-safe — `where` built from hardcoded conditions
            # (`user_id = $1`, optional `entity_type = $N`); user input
            # always parameterized.
            count_row = await conn.fetchrow(
                f"SELECT COUNT(*) AS total FROM audit_logs {where}",
                *(params[:idx]),
            )

        return {
            "items": [_row_to_dict(r) for r in rows],
            "total": count_row["total"],
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        logger.exception("Failed to list audit logs")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/entity/{entity_type}/{entity_id}")
async def audit_for_entity(
    entity_type: str,
    entity_id: UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Audit trail for a specific entity."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM audit_logs
                   WHERE entity_type = $1 AND entity_id = $2
                     AND user_id = $3::uuid
                   ORDER BY created_at DESC
                   LIMIT $4 OFFSET $5""",
                entity_type, entity_id, user_id, limit, offset,
            )
            count_row = await conn.fetchrow(
                """SELECT COUNT(*) AS total FROM audit_logs
                   WHERE entity_type = $1 AND entity_id = $2
                     AND user_id = $3::uuid""",
                entity_type, entity_id, user_id,
            )
        return {
            "items": [_row_to_dict(r) for r in rows],
            "total": count_row["total"],
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        logger.exception("Failed to get audit trail for entity")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/export")
async def export_audit_csv(
    request: Request,
    entity_type: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
):
    """Export audit logs as CSV."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            conditions = ["user_id = $1::uuid"]
            params: list = [user_id]
            if entity_type:
                conditions.append(f"entity_type = ${len(params) + 1}")
                params.append(entity_type)

            where = "WHERE " + " AND ".join(conditions)
            idx = len(params)
            params.append(limit)

            rows = await conn.fetch(
                f"""SELECT * FROM audit_logs
                    {where}
                    ORDER BY created_at DESC
                    LIMIT ${idx + 1}""",
                *params,
            )

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "user_id", "entity_type", "entity_id", "action", "changes", "ip_address", "created_at"])
        for r in rows:
            changes = r["changes"]
            if isinstance(changes, str):
                pass  # already string
            else:
                changes = json.dumps(changes)
            writer.writerow([
                str(r["id"]),
                str(r["user_id"]) if r["user_id"] else "",
                r["entity_type"],
                str(r["entity_id"]),
                r["action"],
                changes,
                r["ip_address"] or "",
                r["created_at"].isoformat(),
            ])

        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to export audit logs")
        raise HTTPException(status_code=500, detail="Internal server error")
