"""Automations — publish workflows to production and execute them."""

import asyncio
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.db.client import get_db_pool

router = APIRouter(prefix="/automations", tags=["automations"])
logger = logging.getLogger(__name__)


def _get_user_id(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        data = verify_token(auth[7:])
        if data:
            return data.get("sub")
    return None


class PublishRequest(BaseModel):
    workflow_id: UUID
    name: str
    description: Optional[str] = None
    icon: str = "⚡"
    color: str = "#6366F1"
    trigger_type: str = "manual"
    schedule_cron: Optional[str] = None


class UpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    trigger_type: Optional[str] = None
    schedule_cron: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_automations(request: Request):
    """List user's published automations. Returns empty list for guests."""
    user_id = _get_user_id(request)
    if not user_id:
        return []
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT a.id, a.workflow_id, a.name, a.description, a.icon, a.color,
                          a.trigger_type, a.schedule_cron, a.is_active,
                          a.total_runs, a.last_run_at, a.created_at,
                          w.name AS workflow_name, w.status AS workflow_status
                   FROM automations a
                   JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.user_id = $1::uuid
                   ORDER BY a.created_at DESC""",
                user_id,
            )
        return [
            {
                "id": str(r["id"]),
                "workflow_id": str(r["workflow_id"]),
                "workflow_name": r["workflow_name"],
                "workflow_status": r["workflow_status"],
                "name": r["name"],
                "description": r["description"],
                "icon": r["icon"],
                "color": r["color"],
                "trigger_type": r["trigger_type"],
                "schedule_cron": r["schedule_cron"],
                "is_active": r["is_active"],
                "total_runs": r["total_runs"],
                "last_run_at": r["last_run_at"].isoformat() if r["last_run_at"] else None,
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.exception("Failed to list automations")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/", status_code=201)
async def publish_automation(body: PublishRequest, request: Request):
    """Publish a workflow as a production automation."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify workflow belongs to user (or is accessible)
            wf = await conn.fetchrow(
                "SELECT id, name FROM workflows WHERE id = $1", body.workflow_id
            )
            if not wf:
                raise HTTPException(status_code=404, detail="Workflow not found")

            row = await conn.fetchrow(
                """INSERT INTO automations
                       (user_id, workflow_id, name, description, icon, color,
                        trigger_type, schedule_cron)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8)
                   RETURNING id, created_at""",
                user_id, body.workflow_id, body.name, body.description,
                body.icon, body.color, body.trigger_type, body.schedule_cron,
            )
        return {"id": str(row["id"]), "created_at": row["created_at"].isoformat()}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to publish automation")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/{automation_id}")
async def update_automation(automation_id: UUID, body: UpdateRequest, request: Request):
    """Update automation config."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM automations WHERE id = $1 AND user_id = $2::uuid",
                automation_id, user_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Automation not found")

            updates = {k: v for k, v in body.model_dump().items() if v is not None}
            if not updates:
                return {"updated": False}

            set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
            values = list(updates.values())
            await conn.execute(
                f"UPDATE automations SET {set_clauses}, updated_at = now() WHERE id = $1",
                automation_id, *values,
            )
        return {"updated": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update automation")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{automation_id}")
async def delete_automation(automation_id: UUID, request: Request):
    """Unpublish (delete) an automation. The underlying workflow is kept."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM automations WHERE id = $1 AND user_id = $2::uuid",
                automation_id, user_id,
            )
        deleted = int(result.split()[-1]) > 0
        if not deleted:
            raise HTTPException(status_code=404, detail="Automation not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete automation")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{automation_id}/run", status_code=201)
async def run_automation(automation_id: UUID, request: Request):
    """Execute an automation — creates a workflow_run and launches execution."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                """SELECT a.workflow_id, a.name, w.dag_definition, w.name AS wf_name
                   FROM automations a JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.id = $1 AND (a.user_id = $2::uuid OR $2 IS NULL)""",
                automation_id, user_id,
            )
            if not auto:
                raise HTTPException(status_code=404, detail="Automation not found")

            dag_data = auto["dag_definition"]
            if isinstance(dag_data, str):
                dag_data = json.loads(dag_data)
            from app.models.workflow import DAGDefinition
            dag = DAGDefinition(**dag_data)

            row = await conn.fetchrow(
                """INSERT INTO workflow_runs (workflow_id, status, trigger_type, metadata)
                   VALUES ($1, 'pending', 'manual', $2::jsonb)
                   RETURNING id, created_at""",
                auto["workflow_id"],
                json.dumps({"automation_id": str(automation_id), "automation_name": auto["name"]}),
            )
            run_id = row["id"]

            # Update stats
            await conn.execute(
                "UPDATE automations SET total_runs = total_runs + 1, last_run_at = now() WHERE id = $1",
                automation_id,
            )

        from app.infrastructure.tracking.metrics_collector_tracker import MetricsCollectorTracker
        from app.infrastructure.tracking.safe_tracker import SafeExecutionTracker
        from app.domain.tracking.events import ExecutionContext
        from app.engine.executor import execute_workflow

        tracker = SafeExecutionTracker(MetricsCollectorTracker())
        ctx = ExecutionContext(
            run_id=str(run_id),
            workflow_name=auto["wf_name"] or auto["name"],
            tracker=tracker,
        )
        asyncio.create_task(
            execute_workflow(auto["workflow_id"], run_id, dag, {}, ctx=ctx, user_id=user_id)
        )

        return {"run_id": str(run_id), "status": "pending"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to run automation")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{automation_id}/stats")
async def get_automation_stats(automation_id: UUID, request: Request):
    """Return run stats for an automation."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                "SELECT workflow_id, total_runs, last_run_at FROM automations WHERE id = $1",
                automation_id,
            )
            if not auto:
                raise HTTPException(status_code=404, detail="Automation not found")

            agg = await conn.fetchrow(
                """SELECT
                       count(*) FILTER (WHERE status = 'completed') AS completed,
                       count(*) FILTER (WHERE status = 'failed') AS failed,
                       avg(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)
                           FILTER (WHERE status = 'completed') AS avg_duration_ms,
                       avg(total_cost_usd) FILTER (WHERE status = 'completed') AS avg_cost
                   FROM workflow_runs
                   WHERE workflow_id = $1""",
                auto["workflow_id"],
            )

        return {
            "total_runs": auto["total_runs"],
            "last_run_at": auto["last_run_at"].isoformat() if auto["last_run_at"] else None,
            "completed": int(agg["completed"] or 0),
            "failed": int(agg["failed"] or 0),
            "avg_duration_ms": round(float(agg["avg_duration_ms"] or 0)),
            "avg_cost_usd": round(float(agg["avg_cost"] or 0), 5),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get automation stats")
        raise HTTPException(status_code=500, detail=str(exc))
