"""Lightweight helper to record use-case executions in workflow_runs + step_executions.

Usage in any route:

    run_id = await start_run("Enterprise Ops Pipeline")
    await record_step(run_id, "IntakeAgent", "intake", tokens_used=120, cost_usd=0.001, duration_ms=45)
    await record_step(run_id, "ClassifierAgent", "classifier", ...)
    await complete_run(run_id, total_tokens=500, total_cost_usd=0.005)
"""

import json
import logging
from uuid import UUID, uuid4
from app.db.client import get_db_pool

logger = logging.getLogger(__name__)


async def start_run(workflow_name: str, trigger_type: str = "manual", metadata: dict = None) -> UUID:
    """Create a workflow_run record and return its id."""
    pool = await get_db_pool()
    run_id = uuid4()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO workflow_runs (id, workflow_id, status, trigger_type, started_at, metadata)
               VALUES ($1, NULL, 'running', $2, now(), $3::jsonb)""",
            run_id, trigger_type, json.dumps({"workflow_name": workflow_name, **(metadata or {})}),
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


async def complete_run(
    run_id: UUID,
    status: str = "completed",
    total_tokens: int = 0,
    total_cost_usd: float = 0.0,
    error_message: str = None,
) -> None:
    """Finalize a workflow_run with totals."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE workflow_runs
               SET status = $1, total_tokens = $2, total_cost_usd = $3,
                   error_message = $4, completed_at = now()
               WHERE id = $5""",
            status, total_tokens, total_cost_usd, error_message, run_id,
        )
