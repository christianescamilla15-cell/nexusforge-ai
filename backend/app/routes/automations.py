"""Automations — publish workflows to production and execute them."""

import asyncio
import json
import logging
import secrets
from datetime import datetime
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
        # C-1 (2026-04-25): if a user_id is provided, verify the workflow
        # belongs to it. Webhook + scheduler paths pass the automation's
        # owning user_id (resolved upstream), so this guard catches a bad
        # link even if `publish_automation`'s ownership check was somehow
        # bypassed. Defense in depth.
        if user_id:
            wf = await conn.fetchrow(
                "SELECT dag_definition FROM workflows WHERE id = $1 AND user_id = $2::uuid",
                workflow_id, user_id,
            )
        else:
            wf = await conn.fetchrow(
                "SELECT dag_definition FROM workflows WHERE id = $1", workflow_id
            )
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")

        dag_data = wf["dag_definition"]
        if isinstance(dag_data, str):
            dag_data = json.loads(dag_data)
        dag = DAGDefinition(**dag_data)

        # Parse user_id to UUID for the column
        uid = None
        if user_id:
            try:
                from uuid import UUID as _UUID
                uid = _UUID(user_id) if isinstance(user_id, str) else user_id
            except (ValueError, AttributeError):
                uid = None

        row = await conn.fetchrow(
            """INSERT INTO workflow_runs
               (workflow_id, status, trigger_type, metadata, user_id, automation_id, pipeline_name, execution_type)
               VALUES ($1, 'pending', 'manual', $2::jsonb, $3, $4, $5, 'automation')
               RETURNING id""",
            workflow_id,
            json.dumps({"automation_id": str(automation_id), "automation_name": auto_name}),
            uid,
            automation_id,
            auto_name,
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
            # Dispatch outputs to configured destinations (best-effort)
            try:
                from app.integrations.output_dispatch import dispatch_outputs
                p = await get_db_pool()
                async with p.acquire() as c:
                    wr = await c.fetchrow(
                        "SELECT total_tokens, total_cost_usd, agents_used, status FROM workflow_runs WHERE id = $1",
                        run_id,
                    )
                if wr:
                    agents = wr["agents_used"]
                    if isinstance(agents, str):
                        agents = json.loads(agents)
                    await dispatch_outputs(
                        automation_id=automation_id,
                        run_id=run_id,
                        user_id=user_id or "",
                        result_summary={
                            "status": wr["status"],
                            "total_tokens": wr["total_tokens"] or 0,
                            "cost_usd": float(wr["total_cost_usd"] or 0),
                            "agents_used": agents if isinstance(agents, list) else [],
                            "summary": f"{auto_name} completed with {wr['total_tokens'] or 0} tokens",
                        },
                    )
            except Exception as de:
                logger.warning("output_dispatch failed for run %s: %s", run_id, de)
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
    output_config: dict = {}
    requires_approval: bool = False


class UpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    trigger_type: Optional[str] = None
    schedule_cron: Optional[str] = None
    is_active: Optional[bool] = None
    input_config: Optional[dict] = None
    requires_approval: Optional[bool] = None


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
        raise HTTPException(status_code=500, detail="Internal server error")


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
            # C-1 (2026-04-25): caller must own the workflow being published.
            # Without this, an attacker could publish another user's workflow
            # as their own automation, capture the returned webhook_secret,
            # and trigger arbitrary execution of victim DAGs.
            wf = await conn.fetchrow(
                "SELECT id FROM workflows WHERE id = $1 AND user_id = $2::uuid",
                body.workflow_id, user_id,
            )
            if not wf:
                raise HTTPException(status_code=404, detail="Workflow not found")

            row = await conn.fetchrow(
                """INSERT INTO automations
                       (user_id, workflow_id, name, description, icon, color,
                        trigger_type, schedule_cron, input_config, output_config,
                        webhook_secret, requires_approval)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb,
                           $11, $12)
                   RETURNING id, created_at, webhook_secret""",
                user_id, body.workflow_id, body.name, body.description,
                body.icon, body.color, body.trigger_type, body.schedule_cron,
                json.dumps(body.input_config), json.dumps(body.output_config),
                webhook_secret, body.requires_approval,
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
        raise HTTPException(status_code=500, detail="Internal server error")


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

            # Whitelist allowed columns to prevent SQL injection
            _ALLOWED_COLS = {"name", "description", "icon", "color", "trigger_type", "schedule_cron", "is_active", "input_config", "requires_approval"}
            data = {k: v for k, v in data.items() if k in _ALLOWED_COLS}
            if not data:
                return {"updated": False}

            # Serialize input_config to JSON string for asyncpg
            if "input_config" in data:
                data["input_config"] = json.dumps(data["input_config"])

            set_clauses = ", ".join(
                f"{k} = ${i+2}{'::jsonb' if k == 'input_config' else ''}"
                for i, k in enumerate(data)
            )
            # mythos: sqli-safe — explicit `_ALLOWED_COLS` whitelist is
            # applied above (filters `data` to only known columns).
            # Values use positional parameters.
            await conn.execute(
                f"UPDATE automations SET {set_clauses}, updated_at = now() WHERE id = $1",
                automation_id, *data.values(),
            )
        return {"updated": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update automation")
        raise HTTPException(status_code=500, detail="Internal error updating automation")


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
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Output Config ─────────────────────────────────────────────────────────────

@router.get("/{automation_id}/output-config")
async def get_output_config(automation_id: UUID, request: Request):
    """Get output destination config for an automation."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT output_config FROM automations WHERE id = $1 AND user_id = $2::uuid",
            automation_id, user_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    config = row["output_config"] or {}
    if isinstance(config, str):
        config = json.loads(config)
    return {"output_config": config}


@router.put("/{automation_id}/output-config")
async def update_output_config(automation_id: UUID, request: Request):
    """Update output destination config for an automation."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    body = await request.json()
    config = body.get("output_config", {})
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE automations SET output_config = $1::jsonb WHERE id = $2 AND user_id = $3::uuid",
            json.dumps(config), automation_id, user_id,
        )
    if int(result.split()[-1]) == 0:
        raise HTTPException(status_code=404, detail="Automation not found")
    return {"updated": True, "output_config": config}


# ── Run ───────────────────────────────────────────────────────────────────────

@router.post("/{automation_id}/run", status_code=201)
async def run_automation(automation_id: UUID, body: RunRequest, request: Request):
    """Execute an automation with optional input_data. Rate-limited per plan."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required")
    # Rate limit check
    try:
        from app.auth.rate_limit import check_rate_limit
        request.state.user_id = user_id
        request.state.user_plan = "free"  # will be overridden by rate_limit from DB
        await check_rate_limit(request)
    except HTTPException:
        raise
    except Exception:
        pass  # fail open
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                """SELECT a.id, a.workflow_id, a.name, w.name AS wf_name
                   FROM automations a JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.id = $1 AND a.user_id = $2::uuid""",
                automation_id, user_id,
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
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Single automation ─────────────────────────────────────────────────────────

@router.get("/{automation_id}")
async def get_automation(automation_id: UUID, request: Request):
    """Get single automation with workflow DAG."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT a.*, w.dag_definition, w.name AS workflow_name
                   FROM automations a
                   LEFT JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.id = $1""",
                automation_id,
            )
        if not row:
            raise HTTPException(404, "Automation not found")
        if user_id and row.get("user_id") and str(row["user_id"]) != user_id:
            raise HTTPException(403, "Access denied")
        return _row_to_dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ── Stats + Dashboard ─────────────────────────────────────────────────────────

@router.get("/{automation_id}/stats")
async def get_automation_stats(automation_id: UUID, request: Request):
    """Return aggregated run stats for an automation."""
    user_id = _get_user_id(request)
    if not user_id:
        return {"total_runs": 0, "last_run_at": None, "completed": 0, "failed": 0, "avg_duration_ms": 0, "avg_cost_usd": 0}
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                "SELECT workflow_id, total_runs, last_run_at FROM automations WHERE id = $1 AND user_id = $2::uuid",
                automation_id, user_id,
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
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{automation_id}/dashboard")
async def get_automation_dashboard(automation_id: UUID, request: Request):
    """Return full dashboard data: automation info + stats + recent runs."""
    user_id = _get_user_id(request)
    if not user_id:
        return {"automation": {}, "stats": {}, "recent_runs": []}
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                """SELECT a.*, w.name AS workflow_name
                   FROM automations a JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.id = $1 AND a.user_id = $2::uuid""",
                automation_id, user_id,
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
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Webhook trigger ───────────────────────────────────────────────────────────

@router.post("/webhook/{webhook_secret}", status_code=201)
async def handle_webhook_trigger(webhook_secret: str, request: Request):
    """Execute an automation via its webhook URL. Supports HMAC signature verification."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            auto = await conn.fetchrow(
                """SELECT a.id, a.workflow_id, a.name, a.user_id, w.name AS wf_name
                   FROM automations a JOIN workflows w ON w.id = a.workflow_id
                   WHERE a.webhook_secret = $1 AND a.is_active = true""",
                webhook_secret,
            )
        if not auto:
            raise HTTPException(status_code=404, detail="Webhook not found or inactive")

        # Verify HMAC signature if provided (optional but recommended)
        signature = request.headers.get("X-NexusForge-Signature", "")
        body_bytes = await request.body()
        if signature:
            import hmac as _hmac, hashlib as _hashlib
            expected = "sha256=" + _hmac.new(
                webhook_secret.encode(), body_bytes, _hashlib.sha256
            ).hexdigest()
            if not _hmac.compare_digest(signature, expected):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        try:
            input_data = json.loads(body_bytes) if body_bytes else {}
        except Exception:
            input_data = {}

        # C-2 (2026-04-25): inherit the automation owner so the resulting
        # workflow_run row is owned by the automation owner. Previously
        # passed user_id=None → run landed with NULL → world-readable to
        # every account that hits executions_db with `OR user_id IS NULL`.
        run_id = await _launch_run(
            automation_id=auto["id"],
            workflow_id=auto["workflow_id"],
            wf_name=auto["wf_name"],
            auto_name=auto["name"],
            input_data=input_data if isinstance(input_data, dict) else {"data": input_data},
            user_id=str(auto["user_id"]) if auto["user_id"] else None,
        )
        return {"run_id": run_id, "status": "pending"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Webhook trigger failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Scheduler ─────────────────────────────────────────────────────────────────


def _compute_next_run(cron: str, now: datetime | None = None) -> datetime:
    """Return the next UTC datetime that the given cron expression fires.

    T3.2 (2026-04-30 triangulation): the previous homegrown parser
    only honored minute and hour, ignoring DOW / DOM / month — so
    a `30 9 * * 1-5` expression (9:30 weekdays) would fire on
    Saturday and Sunday too. We now delegate to `croniter` which
    is the de-facto Python cron library, handles ranges/lists/steps
    on every field, and matches Vixie cron semantics.

    Returns one hour from `now` if the expression is missing or
    fails to parse — same fail-soft contract as the original so
    a single bad row in `automations.schedule_cron` doesn't kill
    the whole scheduler tick.
    """
    from datetime import datetime, timedelta, timezone
    if now is None:
        now = datetime.now(timezone.utc)

    if not cron or not cron.strip():
        return now + timedelta(hours=1)

    try:
        from croniter import croniter, CroniterBadCronError
    except ImportError:
        # Defensive: production has croniter pinned in requirements.txt;
        # this branch only ever fires in environments that pruned the
        # dep on purpose. Returning a 1-hour fallback keeps the loop
        # alive instead of crashing.
        logger.warning("croniter unavailable; falling back to 1h cadence for cron=%r", cron)
        return now + timedelta(hours=1)

    try:
        iterator = croniter(cron.strip(), now)
        return iterator.get_next(datetime)
    except (CroniterBadCronError, ValueError, KeyError) as exc:
        logger.warning("Invalid cron %r: %s — falling back to 1h", cron, exc)
        return now + timedelta(hours=1)


async def _scheduler_loop():
    """Background task: fire scheduled automations when next_run_at <= now()."""
    from datetime import datetime, timedelta, timezone

    def _next_run(cron: str) -> datetime:
        return _compute_next_run(cron)

    while True:
        await asyncio.sleep(60)
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                due = await conn.fetch(
                    """SELECT a.id, a.workflow_id, a.name, a.schedule_cron, a.user_id,
                              w.name AS wf_name
                       FROM automations a JOIN workflows w ON w.id = a.workflow_id
                       WHERE a.trigger_type = 'schedule' AND a.is_active = true
                         AND a.next_run_at IS NOT NULL AND a.next_run_at <= now()""",
                )
            for auto in due:
                try:
                    # C-2 (2026-04-25): same as webhook path — pass the
                    # automation owner so scheduled runs are owned, not NULL.
                    run_id = await _launch_run(
                        automation_id=auto["id"],
                        workflow_id=auto["workflow_id"],
                        wf_name=auto["wf_name"],
                        auto_name=auto["name"],
                        input_data={},
                        user_id=str(auto["user_id"]) if auto["user_id"] else None,
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
    dag = r.get("dag_definition")
    if isinstance(dag, str):
        try:
            dag = json.loads(dag)
        except Exception:
            dag = None
    result = {
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
        "requires_approval": r.get("requires_approval", False),
    }
    if dag is not None:
        result["dag_definition"] = dag
    return result
