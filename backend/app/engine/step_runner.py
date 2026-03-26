"""Execute a single workflow step — dispatches to the appropriate agent."""

import time
import json
from uuid import UUID, uuid4
from app.engine.retry_policy import RetryPolicy
from app.engine.state_machine import transition_step
from app.engine.checkpoint import save_checkpoint
from app.agents.registry import get_agent
from app.db.client import get_db_pool

async def run_step(run_id: UUID, step_name: str, step_type: str,
                   input_data: dict, config: dict, retry_max: int = 3) -> dict:
    """Execute a single step with retry logic and checkpointing."""
    pool = await get_db_pool()
    step_id = uuid4()

    # Record step start
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO step_executions (id, run_id, step_name, step_type, agent_type, status, input_data, started_at)
               VALUES ($1, $2, $3, $4, $5, 'running', $6, now())""",
            step_id, run_id, step_name, step_type, step_type, json.dumps(input_data)
        )

    policy = RetryPolicy(max_retries=retry_max)
    last_error = None

    for attempt in range(retry_max + 1):
        try:
            start = time.monotonic()

            # Get agent and execute
            agent = get_agent(step_type)
            result = await agent.execute(input_data, config)

            duration_ms = int((time.monotonic() - start) * 1000)

            # Record success
            async with pool.acquire() as conn:
                await conn.execute(
                    """UPDATE step_executions
                       SET status = 'completed', output_data = $1, duration_ms = $2,
                           tokens_used = $3, cost_usd = $4, completed_at = now(), retry_count = $5
                       WHERE id = $6""",
                    json.dumps(result.output), duration_ms,
                    result.tokens_used, result.cost_usd, attempt, step_id
                )

            # Checkpoint
            await save_checkpoint(run_id, step_name, {"status": "completed", "output": result.output})

            return {
                "step_name": step_name,
                "status": "completed",
                "output": result.output,
                "tokens_used": result.tokens_used,
                "cost_usd": result.cost_usd,
                "duration_ms": duration_ms,
                "retries": attempt,
            }

        except Exception as e:
            last_error = e
            if policy.should_retry(attempt, e):
                # Mark as retrying
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE step_executions SET status = 'retrying', retry_count = $1, error_message = $2 WHERE id = $3",
                        attempt + 1, str(e), step_id
                    )
                await policy.wait(attempt)
            else:
                break

    # All retries exhausted — mark failed
    duration_ms = int((time.monotonic() - start) * 1000) if 'start' in dir() else 0
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE step_executions
               SET status = 'failed', error_message = $1, duration_ms = $2,
                   retry_count = $3, completed_at = now()
               WHERE id = $4""",
            str(last_error), duration_ms, retry_max, step_id
        )
        # Dead letter
        await conn.execute(
            """INSERT INTO dead_letters (run_id, step_name, payload, error_message, retry_count)
               VALUES ($1, $2, $3, $4, $5)""",
            run_id, step_name, json.dumps(input_data), str(last_error), retry_max
        )

    return {
        "step_name": step_name,
        "status": "failed",
        "error": str(last_error),
        "retries": retry_max,
    }
