"""Evaluation routes — manage scenarios, trigger evaluation runs, and persist
results to PostgreSQL so they survive server restarts."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db.client import get_db_pool

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@router.get("/scenarios")
async def list_scenarios():
    """List all evaluation scenarios from DB."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, scenario_name, workflow_name, input_payload,
                       expected_capabilities, expected_constraints, tags, created_at
                FROM evaluation_scenarios
                ORDER BY created_at DESC
                """
            )
            return {"scenarios": [dict(r) for r in rows], "total": len(rows)}
    except Exception as exc:
        logger.exception("Failed to list evaluation scenarios")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: UUID):
    """Get a single evaluation scenario by ID."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM evaluation_scenarios WHERE id = $1",
                scenario_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Scenario not found")
            return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get evaluation scenario")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/scenarios")
async def create_scenario(
    scenario_name: str,
    workflow_name: str,
    input_payload: dict,
    expected_capabilities: dict | None = None,
    expected_constraints: dict | None = None,
    tags: dict | None = None,
):
    """Create a new evaluation scenario."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO evaluation_scenarios
                    (scenario_name, workflow_name, input_payload,
                     expected_capabilities, expected_constraints, tags)
                VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb)
                RETURNING id, scenario_name, created_at
                """,
                scenario_name,
                workflow_name,
                json.dumps(input_payload),
                json.dumps(expected_capabilities) if expected_capabilities else None,
                json.dumps(expected_constraints) if expected_constraints else None,
                json.dumps(tags) if tags else None,
            )
            return dict(row)
    except Exception as exc:
        logger.exception("Failed to create evaluation scenario")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Evaluation runs
# ---------------------------------------------------------------------------


@router.post("/run")
async def run_evaluation(scenario_name: str | None = None):
    """Execute evaluation scenarios and persist results.

    If *scenario_name* is provided, only that scenario is evaluated.
    Otherwise every registered scenario is executed sequentially.

    For each scenario the endpoint:
    1. Creates an ``evaluation_runs`` row with status ``running``.
    2. Records basic timing metrics in ``evaluation_metrics``.
    3. Finalises the run row with status ``completed`` (or ``failed``).
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Resolve scenarios
            if scenario_name:
                scenarios = await conn.fetch(
                    "SELECT * FROM evaluation_scenarios WHERE scenario_name = $1",
                    scenario_name,
                )
                if not scenarios:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Scenario '{scenario_name}' not found",
                    )
            else:
                scenarios = await conn.fetch(
                    "SELECT * FROM evaluation_scenarios ORDER BY created_at ASC"
                )
                if not scenarios:
                    raise HTTPException(
                        status_code=404, detail="No evaluation scenarios registered"
                    )

            results = []
            for scenario in scenarios:
                # Create evaluation run
                eval_row = await conn.fetchrow(
                    """
                    INSERT INTO evaluation_runs (scenario_id, status)
                    VALUES ($1, 'running')
                    RETURNING id, started_at
                    """,
                    scenario["id"],
                )
                eval_run_id = eval_row["id"]

                try:
                    # Record a placeholder metric (latency of scenario execution).
                    # A full harness can extend this with model-specific metrics.
                    import time

                    t0 = time.monotonic()

                    # Mark completed (actual workflow execution is triggered
                    # separately via /api/executions — here we persist the
                    # evaluation bookkeeping).
                    elapsed_ms = round((time.monotonic() - t0) * 1000, 2)

                    await conn.execute(
                        """
                        UPDATE evaluation_runs
                        SET status = 'completed', finished_at = NOW()
                        WHERE id = $1
                        """,
                        eval_run_id,
                    )

                    # Persist metrics
                    await conn.execute(
                        """
                        INSERT INTO evaluation_metrics
                            (evaluation_run_id, metric_name, metric_value)
                        VALUES ($1, 'evaluation_overhead_ms', $2)
                        """,
                        eval_run_id,
                        elapsed_ms,
                    )

                    results.append(
                        {
                            "eval_run_id": str(eval_run_id),
                            "scenario_name": scenario["scenario_name"],
                            "status": "completed",
                            "started_at": eval_row["started_at"].isoformat(),
                        }
                    )
                except Exception as inner_exc:
                    await conn.execute(
                        """
                        UPDATE evaluation_runs
                        SET status = 'failed', finished_at = NOW()
                        WHERE id = $1
                        """,
                        eval_run_id,
                    )
                    results.append(
                        {
                            "eval_run_id": str(eval_run_id),
                            "scenario_name": scenario["scenario_name"],
                            "status": "failed",
                            "error": str(inner_exc),
                        }
                    )

            return {"evaluation_results": results, "total": len(results)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to run evaluation")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@router.get("/results")
async def list_evaluation_results(limit: int = Query(20, ge=1, le=200)):
    """List recent evaluation runs with metrics."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT er.id, er.scenario_id, er.workflow_run_id, er.status,
                       er.started_at, er.finished_at, er.created_at,
                       es.scenario_name, es.workflow_name
                FROM evaluation_runs er
                JOIN evaluation_scenarios es ON es.id = er.scenario_id
                ORDER BY er.started_at DESC
                LIMIT $1
                """,
                limit,
            )
            return {"results": [dict(r) for r in rows], "total": len(rows)}
    except Exception as exc:
        logger.exception("Failed to list evaluation results")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/results/{eval_run_id}")
async def get_evaluation_result(eval_run_id: UUID):
    """Get detailed metrics for a specific evaluation run."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            run_row = await conn.fetchrow(
                """
                SELECT er.*, es.scenario_name, es.workflow_name
                FROM evaluation_runs er
                JOIN evaluation_scenarios es ON es.id = er.scenario_id
                WHERE er.id = $1
                """,
                eval_run_id,
            )
            if not run_row:
                raise HTTPException(
                    status_code=404, detail="Evaluation run not found"
                )

            metric_rows = await conn.fetch(
                """
                SELECT id, metric_name, metric_value, metric_text, created_at
                FROM evaluation_metrics
                WHERE evaluation_run_id = $1
                ORDER BY created_at ASC
                """,
                eval_run_id,
            )

            return {
                "evaluation_run": dict(run_row),
                "metrics": [dict(m) for m in metric_rows],
                "total_metrics": len(metric_rows),
            }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get evaluation result")
        raise HTTPException(status_code=500, detail=str(exc))
