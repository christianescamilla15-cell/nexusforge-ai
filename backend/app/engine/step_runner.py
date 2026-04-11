"""Execute a single workflow step — dispatches to the appropriate agent."""

import json
import logging
import time
from uuid import UUID, uuid4

from app.agents.registry import get_agent
from app.auth.encryption import decrypt_api_key
from app.db.client import get_db_pool
from app.domain.tracking.events import ExecutionContext
from app.engine.checkpoint import save_checkpoint
from app.engine.retry_policy import RetryPolicy
from app.engine.state_machine import transition_step
from app.healing.healer import SelfHealer

logger = logging.getLogger(__name__)


async def _load_user_agent_config(user_id: str | None, agent_type: str) -> dict:
    """Fetch user's saved agent config from DB. Returns {} if none."""
    if not user_id:
        return {}
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT provider, model, temperature, max_tokens, system_prompt, tools "
                "FROM agent_configs WHERE user_id = $1::uuid AND agent_type = $2",
                user_id, agent_type,
            )
        if not row:
            return {}
        # Also fetch the user's API key for the chosen provider
        async with pool.acquire() as conn:
            key_row = await conn.fetchrow(
                "SELECT api_key_encrypted FROM user_provider_keys "
                "WHERE user_id = $1::uuid AND provider = $2 AND is_active = true",
                user_id, row["provider"],
            )
        return {
            "provider": row["provider"],
            "model": row["model"],
            "temperature": float(row["temperature"]),
            "max_tokens": row["max_tokens"],
            "system_prompt": row["system_prompt"],
            "tools": row["tools"] or [],
            "user_api_key": decrypt_api_key(key_row["api_key_encrypted"]) if key_row else None,
        }
    except Exception as exc:
        logger.debug("Could not load user agent config for %s/%s: %s", user_id, agent_type, exc)
        return {}

async def run_step(run_id: UUID, step_name: str, step_type: str,
                   input_data: dict, config: dict, retry_max: int = 3,
                   ctx: ExecutionContext = None, step_order: int = 0,
                   user_id: str = None) -> dict:
    """Execute a single step with retry logic and checkpointing."""
    pool = await get_db_pool()
    step_id = uuid4()

    # Merge user's saved agent config on top of workflow-level config
    user_cfg = await _load_user_agent_config(user_id, step_type)
    merged_config = {**config, **user_cfg}

    # State machine enforcement — step is conceptually PENDING before
    # it is inserted, and transitions to RUNNING on insert. The tracked
    # variable catches state drift that would otherwise go silent.
    current_step_status = transition_step("pending", "running")

    # Record step start
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO step_executions (id, run_id, step_name, step_type, agent_type, status, input_data, started_at)
               VALUES ($1, $2, $3, $4, $5, 'running', $6, now())""",
            step_id, run_id, step_name, step_type, step_type, json.dumps(input_data)
        )

    # Tracking: step started
    if ctx and ctx.tracker:
        await ctx.tracker.step_started(
            run_id=str(run_id),
            step_id=str(step_id),
            step_order=step_order,
            agent_name=step_type,
            input_payload=input_data,
        )

    policy = RetryPolicy(max_retries=retry_max)
    last_error = None

    for attempt in range(retry_max + 1):
        # At the start of each attempt the step is conceptually RUNNING.
        # If the previous iteration marked it RETRYING, normalize the
        # tracked state back to RUNNING (retrying → running is a valid
        # transition). No DB write — the row was not updated during
        # the retry_policy.wait either. This keeps multi-retry flows
        # legal in the state machine.
        if current_step_status == "retrying":
            current_step_status = transition_step(current_step_status, "running")

        try:
            start = time.monotonic()

            # Get agent and execute
            agent = get_agent(step_type)
            result = await agent.run(input_data, merged_config)

            duration_ms = int((time.monotonic() - start) * 1000)

            # Record success — running → completed
            current_step_status = transition_step(current_step_status, "completed")
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
            await save_checkpoint(run_id, step_name, {"status": "completed", "output": result.output},
                                  ctx=ctx, step_id=str(step_id))

            # Tracking: step completed
            if ctx and ctx.tracker:
                await ctx.tracker.step_completed(
                    step_id=str(step_id),
                    output_payload=result.output if isinstance(result.output, dict) else None,
                    tokens_used=result.tokens_used,
                    cost_usd=result.cost_usd,
                )

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
                # Mark as retrying — running → retrying
                current_step_status = transition_step(current_step_status, "retrying")
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE step_executions SET status = 'retrying', retry_count = $1, error_message = $2 WHERE id = $3",
                        attempt + 1, str(e), step_id
                    )
                # Tracking: retry recorded
                if ctx and ctx.tracker:
                    await ctx.tracker.retry_recorded(step_id=str(step_id), attempt=attempt + 1)
                await policy.wait(attempt)
            else:
                break

    # All retries exhausted — attempt self-healing before dead letter queue
    duration_ms = int((time.monotonic() - start) * 1000) if 'start' in locals() else 0

    failed_step_info = {
        "step_name": step_name,
        "step_type": step_type,
        "input_data": input_data,
        "config": config,
    }
    error_info = {
        "error_message": str(last_error),
        "error": last_error,
        "retry_count": retry_max,
    }
    # Build result_cache from dependency outputs already in input_data
    result_cache = {
        k.strip("_").replace("_output", ""): v
        for k, v in input_data.items()
        if k.startswith("_") and k.endswith("_output")
    }
    execution_context = {
        "run_id": str(run_id),
        "step_id": str(step_id),
        "result_cache": result_cache,
    }

    try:
        heal_result = await SelfHealer().attempt_heal(
            failed_step=failed_step_info,
            error_info=error_info,
            execution_context=execution_context,
        )
    except Exception as heal_exc:
        logger.error("SelfHealer raised an unexpected error for step '%s': %s", step_name, heal_exc)
        heal_result = None

    if heal_result and heal_result.success:
        # Recovery succeeded — mark step as healed (running → completed)
        current_step_status = transition_step(current_step_status, "completed")
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE step_executions
                   SET status = 'completed', output_data = $1, duration_ms = $2,
                       retry_count = $3, completed_at = now(),
                       error_message = $4
                   WHERE id = $5""",
                json.dumps(heal_result.output), duration_ms,
                retry_max, f"healed via {heal_result.strategy_used}", step_id
            )

        await save_checkpoint(run_id, step_name,
                              {"status": "healed", "output": heal_result.output},
                              ctx=ctx, step_id=str(step_id))

        if ctx and ctx.tracker:
            await ctx.tracker.step_completed(
                step_id=str(step_id),
                output_payload=heal_result.output if isinstance(heal_result.output, dict) else None,
                tokens_used=0,
                cost_usd=0.0,
            )

        logger.info("Self-healing succeeded for step '%s' via strategy '%s'", step_name, heal_result.strategy_used)
        return {
            "step_name": step_name,
            "status": "healed",
            "output": heal_result.output,
            "strategy_used": heal_result.strategy_used,
            "retries": retry_max,
            "duration_ms": duration_ms,
        }

    # Healing not available or failed — log reason before dead letter queue
    if heal_result:
        logger.warning(
            "Self-healing failed for step '%s' (strategy: %s): %s",
            step_name, heal_result.strategy_used, heal_result.message,
        )

    # Mark failed and write to dead letter queue — running → failed
    current_step_status = transition_step(current_step_status, "failed")
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

    # Tracking: step failed
    if ctx and ctx.tracker:
        await ctx.tracker.step_failed(step_id=str(step_id), error_message=str(last_error))

    return {
        "step_name": step_name,
        "status": "failed",
        "error": str(last_error),
        "retries": retry_max,
    }
