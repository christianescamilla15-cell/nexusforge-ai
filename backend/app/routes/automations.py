"""Automations — publish workflows to production and execute them."""

import asyncio
import json
import logging
import secrets
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.db.client import get_db_pool

router = APIRouter(prefix="/automations", tags=["automations"])
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user_id(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        data = verify_token(auth[7:])
        if data:
            return data.get("sub")
    return None


async def _launch_run(automation_id: UUID, workflow_id: UUID, wf_name: str,
                      auto_name: str, input_data: dict, user_id: Optional[str]) -> str:
    """Create a workflow_run record and launch execute_workflow. Returns run_id."""
    from app.domain.tracking.events import ExecutionContext
    from app.engine.executor import execute_workflow
    from app.infrastructure.tracking.metrics_collector_tracker import MetricsCollectorTracker
    from app.infrastructure.tracking.safe_tracker import SafeExecutionTracker
    from app.models.workflow import DAGDefinition

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        wf = await conn.fetchrow(
            "SELECT dag_definition FROM workflows WHERE id = $1", workflow_id
        )
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")

        dag_data = wf["dag_definition"]
        if isinstance(dag_data, str):
            dag_data = json.loads(dag_data)
        dag = DAGDefinition(**dag_data)

        row = await conn.fetchrow(
            """INSERT INTO workflow_runs (workflow_id, status, trigger_type, metadata)
               VALUES ($1, 'pending', 'manual', $2::jsonb)
               RETURNING id""",
            workflow_id,
            json.dumps({"automation_id": str(automation_id), "automation_name": auto_name}),
        )
        run_id = row["id"]

        await conn.execute(
            "UPDATE automations SET total_runs = total_runs + 1, last_run_at = now() WHERE id = $1",
            automation_id,
        )

    tracker = SafeExecutionTracker(MetricsCollectorTracker())
    ctx = ExecutionContext(run_id=str(run_id), workflow_name=wf_name or auto_name, tracker=tracker)

    async def _safe_execute():
        try:
            await execute_workflow(workflow_id, run_id, dag, input_data, ctx=ctx, user_id=user_id)
        except Exception as exc:
            logger.exception("Background execution failed for run %s", run_id)
            try:
                p = await get_db_pool()
                async with p.acquire() as c:
                    await c.execute(
                        "UPDATE workflow_runs SET status='failed', error_message=$1, completed_at=now() WHERE id=$2",
                        str(exc), run_id,
                    )
            except Exception:
                logger.exception("Failed to mark run %s as failed in DB", run_id)

    asyncio.create_task(_safe_execute())
    return str(run_id)


# ── Models ────────────────────────────────────────────────────────────────────

class PublishRequest(BaseModel):
    workflow_id: UUID
    name: str
    description: Optional[str] = None
    icon: str = "⚡"
    color: str = "#6366F1"
    trigger_type: str = "manual"
    schedule_cron: Optional[str] = None
    input_config: dict = {"type": "none"}


class UpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    trigger_type: Optional[str] = None
    schedule_cron: Optional[str] = None
    is_active: Optional[bool] = None
    input_config: Optional[dict] = None


class RunRequest(BaseModel):
    input_data: dict = {}


# ── CRUD ──────────────────────────────────────────────────────────────────────

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
                          a.trigger_type, a.schedule_cron, a.is_active, a.input_config,
                          a.webhook_secret, a.total_runs, a.last_run_at, a.created_at,
                          w.name AS workflow_name, w.status AS workflow_status
                   FROM automations a
                   JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.user_id = $1::uuid
                   ORDER BY a.created_at DESC""",
                user_id,
            )
        return [_row_to_dict(r) for r in rows]
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
        # Auto-generate webhook secret for webhook triggers
        webhook_secret = secrets.token_urlsafe(24) if body.trigger_type == "webhook" else None

        async with pool.acquire() as conn:
            wf = await conn.fetchrow("SELECT id FROM workflows WHERE id = $1", body.workflow_id)
            if not wf:
                raise HTTPException(status_code=404, detail="Workflow not found")

            row = await conn.fetchrow(
                """INSERT INTO automations
                       (user_id, workflow_id, name, description, icon, color,
                        trigger_type, schedule_cron, input_config, webhook_secret)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10)
                   RETURNING id, created_at, webhook_secret""",
                user_id, body.workflow_id, body.name, body.description,
                body.icon, body.color, body.trigger_type, body.schedule_cron,
                json.dumps(body.input_config), webhook_secret,
            )
        return {
            "id": str(row["id"]),
            "created_at": row["created_at"].isoformat(),
            "webhook_secret": row["webhook_secret"],
        }
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

            data = body.model_dump(exclude_none=True)
            if not data:
                return {"updated": False}

            # Serialize input_config to JSON string for asyncpg
            if "input_config" in data:
                data["input_config"] = json.dumps(data["input_config"])

            set_clauses = ", ".join(
                f"{k} = ${i+2}{'::jsonb' if k == 'input_config' else ''}"
                for i, k in enumerate(data)
            )
            await conn.execute(
                f"UPDATE automations SET {set_clauses}, updated_at = now() WHERE id = $1",
                automation_id, *data.values(),
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
        if int(result.split()[-1]) == 0:
            raise HTTPException(status_code=404, detail="Automation not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete automation")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Run ───────────────────────────────────────────────────────────────────────

@router.post("/{automation_id}/run", status_code=201)
async def run_automation(automation_id: UUID, body: RunRequest, request: Request):
    """Execute an automation with optional input_data."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                """SELECT a.id, a.workflow_id, a.name, w.name AS wf_name
                   FROM automations a JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.id = $1""",
                automation_id,
            )
        if not auto:
            raise HTTPException(status_code=404, detail="Automation not found")

        run_id = await _launch_run(
            automation_id=automation_id,
            workflow_id=auto["workflow_id"],
            wf_name=auto["wf_name"],
            auto_name=auto["name"],
            input_data=body.input_data,
            user_id=user_id,
        )
        return {"run_id": run_id, "status": "pending"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to run automation")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Stats + Dashboard ─────────────────────────────────────────────────────────

@router.get("/{automation_id}/stats")
async def get_automation_stats(automation_id: UUID):
    """Return aggregated run stats for an automation."""
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
                       coalesce(avg(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)
                           FILTER (WHERE status = 'completed'), 0) AS avg_duration_ms,
                       coalesce(avg(total_cost_usd) FILTER (WHERE status = 'completed'), 0) AS avg_cost
                   FROM workflow_runs WHERE workflow_id = $1""",
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


@router.get("/{automation_id}/dashboard")
async def get_automation_dashboard(automation_id: UUID):
    """Return full dashboard data: automation info + stats + recent runs."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                """SELECT a.*, w.name AS workflow_name
                   FROM automations a JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.id = $1""",
                automation_id,
            )
            if not auto:
                raise HTTPException(status_code=404, detail="Automation not found")

            runs = await conn.fetch(
                """SELECT id, status, started_at, completed_at, total_tokens, total_cost_usd, created_at
                   FROM workflow_runs
                   WHERE workflow_id = $1
                   ORDER BY created_at DESC LIMIT 20""",
                auto["workflow_id"],
            )
            stats = await conn.fetchrow(
                """SELECT
                       count(*) AS total_runs,
                       count(*) FILTER (WHERE status = 'completed') AS completed,
                       count(*) FILTER (WHERE status = 'failed') AS failed,
                       coalesce(sum(total_tokens), 0) AS total_tokens,
                       coalesce(sum(total_cost_usd), 0) AS total_cost,
                       coalesce(avg(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000)
                           FILTER (WHERE status = 'completed'), 0) AS avg_duration_ms
                   FROM workflow_runs WHERE workflow_id = $1""",
                auto["workflow_id"],
            )

        auto_dict = _row_to_dict(auto)
        return {
            "automation": auto_dict,
            "stats": {
                "total_runs": int(stats["total_runs"] or 0),
                "completed": int(stats["completed"] or 0),
                "failed": int(stats["failed"] or 0),
                "total_tokens": int(stats["total_tokens"] or 0),
                "total_cost": round(float(stats["total_cost"] or 0), 5),
                "avg_duration_ms": round(float(stats["avg_duration_ms"] or 0)),
                "success_rate": round(
                    int(stats["completed"] or 0) / max(int(stats["total_runs"] or 1), 1) * 100, 1
                ),
            },
            "recent_runs": [
                {
                    "id": str(r["id"]),
                    "status": r["status"],
                    "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                    "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                    "duration_ms": (
                        int((r["completed_at"] - r["started_at"]).total_seconds() * 1000)
                        if r["completed_at"] and r["started_at"] else None
                    ),
                    "total_tokens": r["total_tokens"] or 0,
                    "total_cost_usd": round(float(r["total_cost_usd"] or 0), 5),
                    "created_at": r["created_at"].isoformat(),
                }
                for r in runs
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get automation dashboard")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Webhook trigger ───────────────────────────────────────────────────────────

@router.post("/webhook/{webhook_secret}", status_code=201)
async def handle_webhook_trigger(webhook_secret: str, request: Request):
    """Execute an automation via its webhook URL."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                """SELECT a.id, a.workflow_id, a.name, w.name AS wf_name
                   FROM automations a JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.webhook_secret = $1 AND a.is_active = true""",
                webhook_secret,
            )
        if not auto:
            raise HTTPException(status_code=404, detail="Webhook not found or inactive")

        try:
            input_data = await request.json()
        except Exception:
            input_data = {}

        run_id = await _launch_run(
            automation_id=auto["id"],
            workflow_id=auto["workflow_id"],
            wf_name=auto["wf_name"],
            auto_name=auto["name"],
            input_data=input_data if isinstance(input_data, dict) else {"data": input_data},
            user_id=None,
        )
        return {"run_id": run_id, "status": "pending"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Webhook trigger failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Scheduler ─────────────────────────────────────────────────────────────────

async def _scheduler_loop():
    """Background task: fire scheduled automations when next_run_at <= now()."""
    import re
    from datetime import datetime, timedelta, timezone

    def _next_run(cron: str) -> datetime:
        """Very simple cron: only handles */N minute patterns and fixed hour/day."""
        now = datetime.now(timezone.utc)
        parts = cron.strip().split()
        if len(parts) != 5:
            return now + timedelta(hours=1)
        minute_part = parts[0]
        # */N — every N minutes
        if minute_part.startswith("*/"):
            try:
                n = int(minute_part[2:])
                return now + timedelta(minutes=n)
            except ValueError:
                pass
        # Fixed minute (e.g. "0 9 * * *" — daily at 9:00)
        try:
            minute = int(minute_part) if minute_part != "*" else 0
            hour = int(parts[1]) if parts[1] != "*" else now.hour
            next_dt = now.replace(minute=minute, second=0, microsecond=0)
            if parts[1] != "*":
                next_dt = next_dt.replace(hour=hour)
            if next_dt <= now:
                next_dt += timedelta(days=1)
            return next_dt
        except (ValueError, TypeError):
            return now + timedelta(hours=1)

    while True:
        await asyncio.sleep(60)
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                due = await conn.fetch(
                    """SELECT a.id, a.workflow_id, a.name, a.schedule_cron, w.name AS wf_name
                       FROM automations a JOIN workflows w ON w.id = a.workflow_id
                       WHERE a.trigger_type = 'schedule' AND a.is_active = true
                         AND a.next_run_at IS NOT NULL AND a.next_run_at <= now()""",
                )
            for auto in due:
                try:
                    run_id = await _launch_run(
                        automation_id=auto["id"],
                        workflow_id=auto["workflow_id"],
                        wf_name=auto["wf_name"],
                        auto_name=auto["name"],
                        input_data={},
                        user_id=None,
                    )
                    next_dt = _next_run(auto["schedule_cron"] or "0 9 * * *")
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE automations SET next_run_at = $1 WHERE id = $2",
                            next_dt, auto["id"],
                        )
                    logger.info("Scheduled automation %s fired → run %s", auto["id"], run_id)
                except Exception as exc:
                    logger.warning("Scheduled automation %s failed: %s", auto["id"], exc)
        except Exception as exc:
            logger.debug("Scheduler tick error: %s", exc)


def start_scheduler():
    """Start the background scheduler loop (call once at app startup)."""
    asyncio.create_task(_scheduler_loop())


# ── Internal helper ───────────────────────────────────────────────────────────

def _row_to_dict(r) -> dict:
    ic = r["input_config"]
    if isinstance(ic, str):
        try:
            ic = json.loads(ic)
        except Exception:
            ic = {"type": "none"}
    return {
        "id": str(r["id"]),
        "workflow_id": str(r["workflow_id"]),
        "workflow_name": r.get("workflow_name"),
        "workflow_status": r.get("workflow_status"),
        "name": r["name"],
        "description": r["description"],
        "icon": r["icon"],
        "color": r["color"],
        "trigger_type": r["trigger_type"],
        "schedule_cron": r.get("schedule_cron"),
        "is_active": r["is_active"],
        "input_config": ic or {"type": "none"},
        "webhook_secret": (
            "••••" + r["webhook_secret"][-4:]
            if r.get("webhook_secret") and len(r["webhook_secret"]) > 4
            else None
        ),
        "total_runs": r["total_runs"],
        "last_run_at": r["last_run_at"].isoformat() if r.get("last_run_at") else None,
        "created_at": r["created_at"].isoformat(),
    }
