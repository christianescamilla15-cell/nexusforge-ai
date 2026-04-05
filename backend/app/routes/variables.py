"""Variables routes — CRUD for automation key-value variables."""

import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.db.client import get_db_pool
from app.utils.audit import log_audit

router = APIRouter(prefix="/variables", tags=["variables"])
logger = logging.getLogger(__name__)

MASK = "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    return uid


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _row_to_dict(r, mask_secrets: bool = True) -> dict:
    value = MASK if (mask_secrets and r["is_secret"]) else r["value"]
    return {
        "id": str(r["id"]),
        "automation_id": str(r["automation_id"]),
        "key": r["key"],
        "value": value,
        "is_secret": r["is_secret"],
        "created_at": r["created_at"].isoformat(),
        "updated_at": r["updated_at"].isoformat(),
    }


# ── Models ───────────────────────────────────────────────────────────────────

class CreateVariableRequest(BaseModel):
    automation_id: UUID
    key: str
    value: str = ""
    is_secret: bool = False


class UpdateVariableRequest(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None
    is_secret: Optional[bool] = None


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/automation/{automation_id}")
async def list_variables(automation_id: UUID, request: Request):
    """List all variables for an automation (secrets are masked)."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify automation ownership
            auto = await conn.fetchrow(
                "SELECT id FROM automations WHERE id = $1 AND (user_id = $2::uuid OR user_id IS NULL)",
                automation_id, user_id,
            )
            if not auto:
                raise HTTPException(status_code=404, detail="Automation not found")
            rows = await conn.fetch(
                """SELECT * FROM automation_variables
                   WHERE automation_id = $1
                   ORDER BY key ASC""",
                automation_id,
            )
        return [_row_to_dict(r, mask_secrets=True) for r in rows]
    except Exception as exc:
        logger.exception("Failed to list variables")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/", status_code=201)
async def create_variable(body: CreateVariableRequest, request: Request):
    """Create a new automation variable."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify automation ownership
            auto = await conn.fetchrow(
                "SELECT id FROM automations WHERE id = $1 AND (user_id = $2::uuid OR user_id IS NULL)",
                body.automation_id, user_id,
            )
            if not auto:
                raise HTTPException(status_code=404, detail="Automation not found")

            row = await conn.fetchrow(
                """INSERT INTO automation_variables
                       (automation_id, key, value, is_secret)
                   VALUES ($1, $2, $3, $4)
                   RETURNING id, created_at""",
                body.automation_id, body.key, body.value, body.is_secret,
            )

        await log_audit(
            user_id, "variable", str(row["id"]), "created",
            {"key": body.key, "is_secret": body.is_secret},
            _client_ip(request),
        )
        return {
            "id": str(row["id"]),
            "key": body.key,
            "created_at": row["created_at"].isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create variable")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/{variable_id}")
async def update_variable(variable_id: UUID, body: UpdateVariableRequest, request: Request):
    """Update an existing automation variable."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                """SELECT av.* FROM automation_variables av
                   JOIN automations a ON a.id = av.automation_id
                   WHERE av.id = $1 AND (a.user_id = $2::uuid OR a.user_id IS NULL)""",
                variable_id, user_id,
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Variable not found")

            data = body.model_dump(exclude_none=True)
            if not data:
                return {"updated": False}

            changes = {}
            for k, v in data.items():
                old = existing[k]
                if k == "value" and existing["is_secret"]:
                    changes[k] = {"old": MASK, "new": MASK}
                else:
                    changes[k] = {"old": old, "new": v}

            set_clauses = ", ".join(
                f"{k} = ${i+2}" for i, k in enumerate(data)
            )
            set_clauses += f", updated_at = now()"
            await conn.execute(
                f"UPDATE automation_variables SET {set_clauses} WHERE id = $1",
                variable_id, *data.values(),
            )

        await log_audit(
            user_id, "variable", str(variable_id), "updated",
            changes, _client_ip(request),
        )
        return {"updated": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update variable")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{variable_id}")
async def delete_variable(variable_id: UUID, request: Request):
    """Delete an automation variable."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                """SELECT av.key, av.automation_id FROM automation_variables av
                   JOIN automations a ON a.id = av.automation_id
                   WHERE av.id = $1 AND (a.user_id = $2::uuid OR a.user_id IS NULL)""",
                variable_id, user_id,
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Variable not found")

            await conn.execute(
                "DELETE FROM automation_variables WHERE id = $1", variable_id,
            )

        await log_audit(
            user_id, "variable", str(variable_id), "deleted",
            {"key": existing["key"], "automation_id": str(existing["automation_id"])},
            _client_ip(request),
        )
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete variable")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Variable resolution (used by step_runner) ────────────────────────────────

async def resolve_variables(automation_id: UUID, input_data: dict) -> dict:
    """Replace {{variable_name}} placeholders in input_data values with
    the corresponding automation_variables entries."""
    import re

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT key, value FROM automation_variables WHERE automation_id = $1",
            automation_id,
        )

    if not rows:
        return input_data

    var_map = {r["key"]: r["value"] or "" for r in rows}
    pattern = re.compile(r"\{\{(\w+)\}\}")

    def _replace(obj):
        if isinstance(obj, str):
            return pattern.sub(lambda m: var_map.get(m.group(1), m.group(0)), obj)
        if isinstance(obj, dict):
            return {k: _replace(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_replace(item) for item in obj]
        return obj

    return _replace(input_data)
