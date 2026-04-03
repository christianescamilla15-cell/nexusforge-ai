"""Rules Engine routes — CRUD + evaluate for automation rules."""

import json
import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.db.client import get_db_pool
from app.rules.engine import evaluate_rules

router = APIRouter(prefix="/rules", tags=["rules"])
logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_user_id(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        data = verify_token(auth[7:])
        if data:
            return data.get("sub")
    return None


def _row_to_dict(r) -> dict:
    conditions = r["conditions"]
    if isinstance(conditions, str):
        conditions = json.loads(conditions)
    actions = r["actions"]
    if isinstance(actions, str):
        actions = json.loads(actions)
    return {
        "id": str(r["id"]),
        "automation_id": str(r["automation_id"]),
        "name": r["name"],
        "description": r.get("description"),
        "priority": r["priority"],
        "is_active": r["is_active"],
        "conditions": conditions,
        "actions": actions,
        "created_at": r["created_at"].isoformat(),
    }


# ── Models ───────────────────────────────────────────────────────────────────

class ConditionItem(BaseModel):
    field: str
    operator: str
    value: Any = ""


class ActionItem(BaseModel):
    type: str  # notify, route, set_field, skip_step
    channel: Optional[str] = None
    message: Optional[str] = None
    target_agent: Optional[str] = None
    field: Optional[str] = None
    value: Optional[Any] = None
    step_name: Optional[str] = None


class CreateRuleRequest(BaseModel):
    automation_id: UUID
    name: str
    description: Optional[str] = None
    priority: int = 0
    is_active: bool = True
    conditions: list[ConditionItem] = []
    actions: list[ActionItem] = []


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    conditions: Optional[list[ConditionItem]] = None
    actions: Optional[list[ActionItem]] = None


class EvaluateRequest(BaseModel):
    automation_id: UUID
    input_data: dict = {}


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/automation/{automation_id}")
async def list_rules(automation_id: UUID, request: Request):
    """List all rules for an automation."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM automation_rules
                   WHERE automation_id = $1
                   ORDER BY priority DESC, created_at ASC""",
                automation_id,
            )
        return [_row_to_dict(r) for r in rows]
    except Exception as exc:
        logger.exception("Failed to list rules")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/", status_code=201)
async def create_rule(body: CreateRuleRequest, request: Request):
    """Create a new automation rule."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify automation exists
            auto = await conn.fetchrow(
                "SELECT id FROM automations WHERE id = $1", body.automation_id,
            )
            if not auto:
                raise HTTPException(status_code=404, detail="Automation not found")

            conditions_json = json.dumps([c.model_dump() for c in body.conditions])
            actions_json = json.dumps([a.model_dump(exclude_none=True) for a in body.actions])

            row = await conn.fetchrow(
                """INSERT INTO automation_rules
                       (automation_id, name, description, priority, is_active, conditions, actions)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb)
                   RETURNING id, created_at""",
                body.automation_id, body.name, body.description,
                body.priority, body.is_active,
                conditions_json, actions_json,
            )
        return {
            "id": str(row["id"]),
            "created_at": row["created_at"].isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create rule")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/{rule_id}")
async def update_rule(rule_id: UUID, body: UpdateRuleRequest, request: Request):
    """Update an existing automation rule."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM automation_rules WHERE id = $1", rule_id,
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Rule not found")

            data = body.model_dump(exclude_none=True)
            if not data:
                return {"updated": False}

            # Serialize conditions/actions to JSON strings
            if "conditions" in data:
                data["conditions"] = json.dumps([c if isinstance(c, dict) else c.model_dump() for c in data["conditions"]])
            if "actions" in data:
                data["actions"] = json.dumps([a if isinstance(a, dict) else a.model_dump(exclude_none=True) for a in data["actions"]])

            set_clauses = ", ".join(
                f"{k} = ${i+2}{'::jsonb' if k in ('conditions', 'actions') else ''}"
                for i, k in enumerate(data)
            )
            await conn.execute(
                f"UPDATE automation_rules SET {set_clauses} WHERE id = $1",
                rule_id, *data.values(),
            )
        return {"updated": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update rule")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{rule_id}")
async def delete_rule(rule_id: UUID, request: Request):
    """Delete an automation rule."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM automation_rules WHERE id = $1", rule_id,
            )
        if int(result.split()[-1]) == 0:
            raise HTTPException(status_code=404, detail="Rule not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete rule")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Evaluate ─────────────────────────────────────────────────────────────────

@router.post("/evaluate")
async def evaluate(body: EvaluateRequest, request: Request):
    """Evaluate rules against input data (test mode).

    Returns which rules matched and what actions would execute.
    """
    try:
        matched = await evaluate_rules(body.automation_id, body.input_data)
        return {
            "automation_id": str(body.automation_id),
            "input_data": body.input_data,
            "matched_rules": matched,
            "total_matched": len(matched),
            "total_actions": sum(len(m["actions"]) for m in matched),
        }
    except Exception as exc:
        logger.exception("Failed to evaluate rules")
        raise HTTPException(status_code=500, detail=str(exc))
