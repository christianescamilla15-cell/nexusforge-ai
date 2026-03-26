"""DAG executor — walks workflow graph, runs parallel branches, manages state."""

import asyncio
import json
import time
from uuid import UUID, uuid4
from app.engine.dag import validate_dag, get_parallel_groups, DAGValidationError
from app.engine.step_runner import run_step
from app.engine.state_machine import transition_workflow
from app.engine.checkpoint import get_completed_steps
from app.models.workflow import DAGDefinition
from app.db.client import get_db_pool, get_redis

class ExecutionError(Exception):
    pass

async def execute_workflow(workflow_id: UUID, run_id: UUID, dag: DAGDefinition,
                          input_data: dict = None) -> dict:
    """Execute a complete workflow DAG with parallel group scheduling."""
    pool = await get_db_pool()
    redis = await get_redis()

    # Validate DAG
    try:
        order = validate_dag(dag)
        groups = get_parallel_groups(dag, order)
    except DAGValidationError as e:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_runs SET status = 'failed', error_message = $1, completed_at = now() WHERE id = $2",
                str(e), run_id
            )
        return {"status": "failed", "error": str(e)}

    steps_by_name = {s.name: s for s in dag.steps}

    # Transition to running
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE workflow_runs SET status = 'running', started_at = now() WHERE id = $1",
            run_id
        )

    # Broadcast start event
    await redis.publish(f"run:{run_id}", json.dumps({"event": "run_started", "groups": len(groups)}))

    # Check for completed steps (resume from checkpoint)
    completed = await get_completed_steps(run_id)

    results = {}
    total_tokens = 0
    total_cost = 0.0

    try:
        for group_idx, group in enumerate(groups):
            # Filter out already completed steps
            pending_steps = [name for name in group if name not in completed]

            if not pending_steps:
                continue

            # Broadcast group start
            await redis.publish(f"run:{run_id}", json.dumps({
                "event": "group_started", "group": group_idx, "steps": pending_steps
            }))

            # Build input for each step (merge workflow input + outputs from dependencies)
            async def run_single_step(step_name):
                step = steps_by_name[step_name]
                step_input = {**(input_data or {})}

                # Merge outputs from dependencies
                for dep in step.depends_on:
                    if dep in results and results[dep].get("output"):
                        step_input[f"_{dep}_output"] = results[dep]["output"]

                result = await run_step(
                    run_id=run_id,
                    step_name=step_name,
                    step_type=step.type,
                    input_data=step_input,
                    config=step.config,
                    retry_max=step.retry_max,
                )

                # Broadcast step completion
                await redis.publish(f"run:{run_id}", json.dumps({
                    "event": f"step_{result['status']}",
                    "step": step_name,
                    "duration_ms": result.get("duration_ms", 0),
                    "tokens": result.get("tokens_used", 0),
                }))

                return result

            # Execute group in parallel
            if len(pending_steps) > 1:
                group_results = await asyncio.gather(
                    *[run_single_step(name) for name in pending_steps],
                    return_exceptions=True
                )
            else:
                group_results = [await run_single_step(pending_steps[0])]

            # Process results
            for i, result in enumerate(group_results):
                step_name = pending_steps[i]
                if isinstance(result, Exception):
                    results[step_name] = {"status": "failed", "error": str(result)}
                else:
                    results[step_name] = result
                    total_tokens += result.get("tokens_used", 0)
                    total_cost += result.get("cost_usd", 0)

                # If any step failed, abort remaining
                if results[step_name]["status"] == "failed":
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """UPDATE workflow_runs
                               SET status = 'failed', error_message = $1,
                                   total_tokens = $2, total_cost_usd = $3, completed_at = now()
                               WHERE id = $4""",
                            f"Step '{step_name}' failed: {results[step_name].get('error', 'unknown')}",
                            total_tokens, total_cost, run_id
                        )
                    await redis.publish(f"run:{run_id}", json.dumps({
                        "event": "run_failed", "failed_step": step_name
                    }))
                    return {"status": "failed", "results": results, "total_tokens": total_tokens, "total_cost_usd": total_cost}

        # All steps completed
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE workflow_runs
                   SET status = 'completed', total_tokens = $1, total_cost_usd = $2, completed_at = now()
                   WHERE id = $3""",
                total_tokens, total_cost, run_id
            )

        await redis.publish(f"run:{run_id}", json.dumps({
            "event": "run_completed", "total_tokens": total_tokens, "total_cost_usd": total_cost
        }))

        return {"status": "completed", "results": results, "total_tokens": total_tokens, "total_cost_usd": total_cost}

    except Exception as e:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE workflow_runs SET status = 'failed', error_message = $1, completed_at = now() WHERE id = $2",
                str(e), run_id
            )
        return {"status": "failed", "error": str(e), "results": results}
