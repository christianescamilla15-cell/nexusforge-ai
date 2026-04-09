"""DB-backed execution routes — persistent query endpoints for workflow runs,
steps, events, checkpoints, and unified timeline.

These endpoints read from PostgreSQL (via asyncpg) so data survives server
restarts, complementing the in-memory /api/runs/* routes used for live
dashboards.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.db.client import get_db_pool

router = APIRouter(prefix="/executions-db", tags=["Executions DB"])
logger = logging.getLogger(__name__)


def _get_user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    return uid


@router.get("/")
async def list_executions(request: Request, limit: int = 50):
    """List recent workflow executions from persistent storage."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, workflow_name, status, started_at, finished_at,
                       total_latency_ms, total_tokens, total_cost_usd,
                       fallback_used, retry_count
                FROM workflow_runs
                WHERE user_id = $1::uuid OR user_id IS NULL
                ORDER BY started_at DESC
                LIMIT $2
                """,
                user_id, limit,
            )
            return {"executions": [dict(r) for r in rows], "total": len(rows)}
    except Exception as exc:
        logger.exception("Failed to list executions from DB")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{run_id}")
async def get_execution(run_id: str, request: Request):
    """Get a specific execution by ID."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM workflow_runs WHERE id = $1 AND (user_id = $2::uuid OR user_id IS NULL)",
                run_id, user_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Execution not found")
            return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get execution from DB")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{run_id}/steps")
async def get_execution_steps(run_id: str, request: Request):
    """Get all steps for a specific execution."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify run ownership first
            owner_check = await conn.fetchrow(
                "SELECT id FROM workflow_runs WHERE id = $1 AND (user_id = $2::uuid OR user_id IS NULL)",
                run_id, user_id,
            )
            if not owner_check:
                raise HTTPException(status_code=404, detail="Execution not found")
            rows = await conn.fetch(
                """
                SELECT * FROM workflow_steps
                WHERE run_id = $1
                ORDER BY step_order ASC
                """,
                run_id,
            )
            return {"steps": [dict(r) for r in rows], "total": len(rows)}
    except Exception as exc:
        logger.exception("Failed to get execution steps from DB")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{run_id}/events")
async def get_execution_events(run_id: str, request: Request):
    """Get all agent events for a specific execution."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify run ownership first
            owner_check = await conn.fetchrow(
                "SELECT id FROM workflow_runs WHERE id = $1 AND (user_id = $2::uuid OR user_id IS NULL)",
                run_id, user_id,
            )
            if not owner_check:
                raise HTTPException(status_code=404, detail="Execution not found")
            rows = await conn.fetch(
                """
                SELECT * FROM agent_events
                WHERE run_id = $1
                ORDER BY created_at ASC
                """,
                run_id,
            )
            return {"events": [dict(r) for r in rows], "total": len(rows)}
    except Exception as exc:
        logger.exception("Failed to get execution events from DB")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{run_id}/timeline")
async def get_execution_timeline(run_id: str, request: Request):
    """Get unified timeline merging workflow lifecycle, steps, events, and
    checkpoints — ordered chronologically."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Workflow lifecycle
            run = await conn.fetchrow(
                "SELECT * FROM workflow_runs WHERE id = $1 AND (user_id = $2::uuid OR user_id IS NULL)",
                run_id, user_id,
            )
            if not run:
                raise HTTPException(status_code=404, detail="Execution not found")

            timeline: list[dict] = []

            # --- Workflow start ---
            timeline.append(
                {
                    "timestamp": run["started_at"].isoformat() if run["started_at"] else None,
                    "type": "workflow",
                    "event": "workflow_started",
                    "agent": None,
                    "step_id": None,
                    "payload": {
                        "workflow_name": run["workflow_name"],
                        "status": run["status"],
                    },
                }
            )

            # --- Steps ---
            steps = await conn.fetch(
                """
                SELECT * FROM workflow_steps
                WHERE run_id = $1
                ORDER BY started_at ASC NULLS LAST
                """,
                run_id,
            )
            for step in steps:
                if step["started_at"]:
                    timeline.append(
                        {
                            "timestamp": step["started_at"].isoformat(),
                            "type": "step",
                            "event": "step_started",
                            "agent": step["agent_name"],
                            "step_id": str(step["id"]),
                            "payload": {
                                "step_order": step["step_order"],
                                "status": step["status"],
                            },
                        }
                    )
                if step["finished_at"]:
                    timeline.append(
                        {
                            "timestamp": step["finished_at"].isoformat(),
                            "type": "step",
                            "event": f"step_{step['status']}",
                            "agent": step["agent_name"],
                            "step_id": str(step["id"]),
                            "payload": {
                                "latency_ms": step["latency_ms"],
                                "provider": step["provider_name"],
                            },
                        }
                    )

            # --- Agent events ---
            events = await conn.fetch(
                """
                SELECT * FROM agent_events
                WHERE run_id = $1
                ORDER BY created_at ASC
                """,
                run_id,
            )
            for event in events:
                timeline.append(
                    {
                        "timestamp": event["created_at"].isoformat(),
                        "type": "event",
                        "event": event["event_type"],
                        "agent": event["agent_name"],
                        "step_id": str(event["step_id"]) if event["step_id"] else None,
                        "payload": event["metadata"],
                    }
                )

            # --- Checkpoints ---
            checkpoints = await conn.fetch(
                """
                SELECT * FROM checkpoints
                WHERE run_id = $1
                ORDER BY created_at ASC
                """,
                run_id,
            )
            for cp in checkpoints:
                timeline.append(
                    {
                        "timestamp": cp["created_at"].isoformat(),
                        "type": "checkpoint",
                        "event": cp["checkpoint_name"],
                        "agent": None,
                        "step_id": str(cp["step_id"]) if cp["step_id"] else None,
                        "payload": {"checkpoint_name": cp["checkpoint_name"]},
                    }
                )

            # --- Workflow end ---
            if run["finished_at"]:
                timeline.append(
                    {
                        "timestamp": run["finished_at"].isoformat(),
                        "type": "workflow",
                        "event": f"workflow_{run['status']}",
                        "agent": None,
                        "step_id": None,
                        "payload": {"total_latency_ms": run["total_latency_ms"]},
                    }
                )

            # Sort chronologically
            timeline.sort(key=lambda x: x["timestamp"] or "")

            return {
                "run_id": run_id,
                "timeline": timeline,
                "total_events": len(timeline),
            }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to build execution timeline from DB")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{run_id}/checkpoints")
async def get_execution_checkpoints(run_id: str, request: Request):
    """Get all checkpoints for a specific execution."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify run ownership first
            owner_check = await conn.fetchrow(
                "SELECT id FROM workflow_runs WHERE id = $1 AND (user_id = $2::uuid OR user_id IS NULL)",
                run_id, user_id,
            )
            if not owner_check:
                raise HTTPException(status_code=404, detail="Execution not found")
            rows = await conn.fetch(
                """
                SELECT * FROM checkpoints
                WHERE run_id = $1
                ORDER BY created_at ASC
                """,
                run_id,
            )
            return {"checkpoints": [dict(r) for r in rows], "total": len(rows)}
    except Exception as exc:
        logger.exception("Failed to get execution checkpoints from DB")
        raise HTTPException(status_code=500, detail="Internal server error")
