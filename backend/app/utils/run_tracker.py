"""Lightweight helper to record use-case executions in workflow_runs + step_executions.

Usage in any route:

    run_id = await start_run(
        pipeline_name="enterprise_operations",
        user_id=user_id,
        trigger_type="api",
        metadata={"trigger_source": "enterprise_ops", "file_name": file_name}
    )
    await record_step(run_id, "IntakeAgent", "intake", tokens_used=120, cost_usd=0.001, duration_ms=45)
    await complete_run(run_id, total_tokens=500, total_cost_usd=0.005, agents_used=["intake", "classifier"])
"""

import json
import logging
from uuid import UUID, uuid4
from app.db.client import get_db_pool

logger = logging.getLogger(__name__)


async def start_run(
    workflow_name: str = None,
    trigger_type: str = "manual",
    metadata: dict = None,
    pipeline_name: str = None,
    agents_used: list = None,
    user_id: str = None,
    execution_type: str = "pipeline",
    automation_id: str = None,
) -> UUID:
    """Create a workflow_run record and return its id.

    Args:
        workflow_name: Human-readable name stored in metadata (legacy param, kept for compat)
        trigger_type: How the run was triggered (manual, api, webhook, schedule)
        metadata: Extra JSONB metadata to store
        pipeline_name: Pipeline identifier (e.g. 'enterprise_operations', 'swarm_consensus')
        agents_used: List of agent names used in this run
        user_id: User who triggered the run
        execution_type: Type discriminator (dag_workflow, pipeline, swarm, automation)
        automation_id: Linked automation UUID if triggered from an automation
    """
    pool = await get_db_pool()
    run_id = uuid4()
    name = pipeline_name or workflow_name or "unknown"
    meta = {
        "workflow_name": workflow_name or name,
        **(metadata or {}),
    }

    agents_json = json.dumps(agents_used or [])
    uid = None
    if user_id:
        try:
            from uuid import UUID as _UUID
            uid = _UUID(user_id) if isinstance(user_id, str) else user_id
        except (ValueError, AttributeError):
            uid = None

    auto_id = None
    if automation_id:
        try:
            from uuid import UUID as _UUID
            auto_id = _UUID(automation_id) if isinstance(automation_id, str) else automation_id
        except (ValueError, AttributeError):
            auto_id = None

    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO workflow_runs
               (id, workflow_id, status, trigger_type, started_at, metadata,
                pipeline_name, agents_used, execution_type, user_id, automation_id)
               VALUES ($1, NULL, 'running', $2, now(), $3::jsonb,
                       $4, $5::jsonb, $6, $7, $8)""",
            run_id, trigger_type, json.dumps(meta), name, agents_json,
            execution_type, uid, auto_id,
        )
    return run_id


async def record_step(
    run_id: UUID,
    step_name: str,
    agent_type: str,
    status: str = "completed",
    tokens_used: int = 0,
    cost_usd: float = 0.0,
    duration_ms: int = 0,
    input_data: dict = None,
    output_data: dict = None,
    error_message: str = None,
) -> None:
    """Insert a step_execution record for a single agent step."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO step_executions
               (id, run_id, step_name, step_type, agent_type, status,
                input_data, output_data, error_message,
                tokens_used, cost_usd, duration_ms,
                retry_count, started_at, completed_at)
               VALUES (gen_random_uuid(), $1, $2, $3, $3, $4,
                       $5::jsonb, $6::jsonb, $7,
                       $8, $9, $10,
                       0, now(), now())""",
            run_id, step_name, agent_type, status,
            json.dumps(input_data or {}), json.dumps(output_data or {}), error_message,
            tokens_used, cost_usd, duration_ms,
        )


async def list_runs(pipeline_name: str = None, limit: int = 20) -> list:
    """List recent runs from workflow_runs (unified source). Replaces list_pipeline_runs."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if pipeline_name:
            rows = await conn.fetch(
                """SELECT id, pipeline_name, status, trigger_type, total_tokens, total_cost_usd,
                          agents_used, error_message, started_at, completed_at, metadata
                   FROM workflow_runs WHERE pipeline_name = $1
                   ORDER BY started_at DESC LIMIT $2""",
                pipeline_name, limit,
            )
        else:
            rows = await conn.fetch(
                """SELECT id, pipeline_name, status, trigger_type, total_tokens, total_cost_usd,
                          agents_used, error_message, started_at, completed_at, metadata
                   FROM workflow_runs ORDER BY started_at DESC LIMIT $1""",
                limit,
            )
        results = []
        for r in rows:
            agents = r["agents_used"]
            if isinstance(agents, str):
                agents = json.loads(agents)
            meta = r["metadata"] or {}
            if isinstance(meta, str):
                meta = json.loads(meta)
            latency_ms = 0
            if r["completed_at"] and r["started_at"]:
                latency_ms = int((r["completed_at"] - r["started_at"]).total_seconds() * 1000)
            results.append({
                "id": r["id"],
                "pipeline_name": r["pipeline_name"],
                "status": r["status"],
                "total_tokens": r["total_tokens"] or 0,
                "cost_usd": float(r["total_cost_usd"] or 0),
                "processing_time_ms": latency_ms,
                "agents_used": agents if isinstance(agents, list) else [],
                "created_at": r["started_at"],
                "notion_url": meta.get("notion_url"),
                "error_message": r["error_message"],
            })
        return results


async def complete_run(
    run_id: UUID,
    status: str = "completed",
    total_tokens: int = 0,
    total_cost_usd: float = 0.0,
    error_message: str = None,
    agents_used: list = None,
    notion_url: str = None,
    extra_metadata: dict = None,
) -> None:
    """Finalize a workflow_run with totals.

    Args:
        run_id: The run UUID returned by start_run()
        status: Final status ('completed' or 'failed')
        total_tokens: Total tokens consumed across all steps
        total_cost_usd: Total cost in USD
        error_message: Error message if status is 'failed'
        agents_used: List of agent names (updates the agents_used column)
        notion_url: Notion page URL if created (stored in metadata)
        extra_metadata: Additional metadata to merge into the existing metadata JSONB
    """
    pool = await get_db_pool()

    # Build metadata update if needed
    if notion_url or extra_metadata:
        async with pool.acquire() as conn:
            # Merge extra metadata into existing metadata
            extra = {**(extra_metadata or {})}
            if notion_url:
                extra["notion_url"] = notion_url
            await conn.execute(
                """UPDATE workflow_runs
                   SET status = $1, total_tokens = $2, total_cost_usd = $3,
                       error_message = $4, completed_at = now(),
                       agents_used = CASE WHEN $5::jsonb IS NOT NULL THEN $5::jsonb ELSE agents_used END,
                       metadata = metadata || $6::jsonb
                   WHERE id = $7""",
                status, total_tokens, total_cost_usd, error_message,
                json.dumps(agents_used) if agents_used is not None else None,
                json.dumps(extra),
                run_id,
            )
    else:
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE workflow_runs
                   SET status = $1, total_tokens = $2, total_cost_usd = $3,
                       error_message = $4, completed_at = now(),
                       agents_used = CASE WHEN $5::jsonb IS NOT NULL THEN $5::jsonb ELSE agents_used END
                   WHERE id = $6""",
                status, total_tokens, total_cost_usd, error_message,
                json.dumps(agents_used) if agents_used is not None else None,
                run_id,
            )
