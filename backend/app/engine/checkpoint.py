"""Step-level checkpointing for crash recovery."""

import json
from uuid import UUID
from app.db.client import get_db_pool
from app.domain.tracking.events import ExecutionContext

async def save_checkpoint(run_id: UUID, step_name: str, state: dict,
                          ctx: ExecutionContext = None, step_id: str = None):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO checkpoints (run_id, step_name, state)
               VALUES ($1, $2, $3)
               ON CONFLICT (run_id, step_name)
               DO UPDATE SET state = $3, created_at = now()""",
            run_id, step_name, json.dumps(state)
        )

    # Tracking: checkpoint created
    if ctx and ctx.tracker and step_id:
        await ctx.tracker.checkpoint_created(
            run_id=str(run_id),
            step_id=step_id,
            checkpoint_data=state,
        )

async def load_checkpoint(run_id: UUID, step_name: str) -> dict | None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT state FROM checkpoints WHERE run_id = $1 AND step_name = $2",
            run_id, step_name
        )
        return json.loads(row["state"]) if row else None

async def get_completed_steps(run_id: UUID) -> set[str]:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT step_name FROM step_executions WHERE run_id = $1 AND status = 'completed'",
            run_id
        )
        return {row["step_name"] for row in rows}
