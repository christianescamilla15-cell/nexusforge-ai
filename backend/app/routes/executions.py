"""Execution routes — trigger, list, cancel runs + WebSocket streaming."""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.db.client import get_db_pool
from app.domain.tracking.events import ExecutionContext
from app.engine.executor import execute_workflow
from app.infrastructure.tracking.metrics_collector_tracker import MetricsCollectorTracker
from app.infrastructure.tracking.safe_tracker import SafeExecutionTracker
from app.models.execution import ExecutionTrigger, ExecutionResponse, StepExecutionResponse
from app.models.workflow import DAGDefinition
from app.websocket.manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", status_code=201)
async def trigger_execution(body: ExecutionTrigger):
    """Create a workflow run and enqueue execution in the background."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify workflow exists
            wf = await conn.fetchrow(
                "SELECT id, name, dag_definition FROM workflows WHERE id = $1 AND status = 'active'",
                body.workflow_id,
            )
            if not wf:
                raise HTTPException(status_code=404, detail="Workflow not found or not active")

            # Create run record
            row = await conn.fetchrow(
                """INSERT INTO workflow_runs (workflow_id, status, trigger_type, metadata)
                   VALUES ($1, 'pending', $2, $3::jsonb)
                   RETURNING id, status, created_at""",
                body.workflow_id,
                body.trigger_type,
                json.dumps(body.input_data),
            )

        run_id = row["id"]

        # Parse DAG and launch execution in background
        dag_data = wf["dag_definition"]
        if isinstance(dag_data, str):
            dag_data = json.loads(dag_data)
        dag = DAGDefinition(**dag_data)

        # Build execution context with MetricsCollector tracker so dashboard
        # API routes (/api/runs/*) serve live execution data.
        tracker = SafeExecutionTracker(MetricsCollectorTracker())
        ctx = ExecutionContext(
            run_id=str(run_id),
            workflow_name=wf["name"] if wf["name"] else str(body.workflow_id),
            tracker=tracker,
        )

        asyncio.create_task(execute_workflow(body.workflow_id, run_id, dag, body.input_data, ctx=ctx))

        return {
            "run_id": str(run_id),
            "status": "pending",
            "created_at": row["created_at"].isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to trigger execution")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/cleanup-zombies", status_code=200)
async def cleanup_zombie_runs():
    """Mark all stuck pending/running runs (>10 min old) as failed."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE workflow_runs
                   SET status = 'failed',
                       completed_at = now(),
                       error_message = 'Marked as failed: execution timed out (zombie cleanup)'
                   WHERE status IN ('pending', 'queued', 'running')
                     AND created_at < now() - interval '10 minutes'"""
            )
            count = int(result.split()[-1]) if result else 0
        return {"detail": f"Cleaned up {count} zombie runs", "affected": count}
    except Exception as exc:
        logger.exception("Failed to cleanup zombies")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=list[ExecutionResponse])
async def list_executions(
    workflow_id: UUID | None = Query(None),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List execution runs with optional filters."""
    try:
        pool = await get_db_pool()
        conditions = []
        params = []
        idx = 1

        if workflow_id:
            conditions.append(f"workflow_id = ${idx}")
            params.append(workflow_id)
            idx += 1
        if status:
            conditions.append(f"status = ${idx}")
            params.append(status)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        params.extend([skip, limit])

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""SELECT wr.id, wr.workflow_id, wr.status, wr.trigger_type,
                           wr.started_at, wr.completed_at, wr.error_message,
                           wr.total_tokens, wr.total_cost_usd, wr.metadata, wr.created_at,
                           w.name AS workflow_name
                    FROM workflow_runs wr
                    LEFT JOIN workflows w ON w.id = wr.workflow_id
                    {where.replace('workflow_id', 'wr.workflow_id').replace('status', 'wr.status') if where else ''}
                    ORDER BY wr.created_at DESC
                    OFFSET ${idx} LIMIT ${idx + 1}""",
                *params,
            )

        results = []
        for r in rows:
            meta = r["metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta)
            resp = ExecutionResponse(
                id=r["id"],
                workflow_id=r["workflow_id"],
                status=r["status"],
                trigger_type=r["trigger_type"],
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                error_message=r["error_message"],
                total_tokens=r["total_tokens"] or 0,
                total_cost_usd=float(r["total_cost_usd"] or 0),
                metadata=meta or {},
                created_at=r["created_at"],
                steps=[],
            )
            resp.workflow_name = r.get("workflow_name") or "Workflow"
            results.append(resp)
        return results
    except Exception as exc:
        logger.exception("Failed to list executions")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{run_id}", response_model=ExecutionResponse)
async def get_execution(run_id: UUID):
    """Get a single execution run with all step details."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT wr.id, wr.workflow_id, wr.status, wr.trigger_type,
                          wr.started_at, wr.completed_at, wr.error_message,
                          wr.total_tokens, wr.total_cost_usd, wr.metadata, wr.created_at,
                          w.name AS workflow_name
                   FROM workflow_runs wr
                   LEFT JOIN workflows w ON w.id = wr.workflow_id
                   WHERE wr.id = $1""",
                run_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Execution run not found")

            step_rows = await conn.fetch(
                """SELECT id, step_name, step_type, agent_type, status, input_data, output_data,
                          error_message, retry_count, tokens_used, cost_usd, duration_ms,
                          started_at, completed_at
                   FROM step_executions WHERE run_id = $1
                   ORDER BY started_at ASC NULLS LAST""",
                run_id,
            )

        meta = row["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)

        steps = []
        for s in step_rows:
            inp = s["input_data"]
            if isinstance(inp, str):
                inp = json.loads(inp)
            out = s["output_data"]
            if isinstance(out, str):
                out = json.loads(out)
            steps.append(StepExecutionResponse(
                id=s["id"],
                step_name=s["step_name"],
                step_type=s["step_type"],
                agent_type=s["agent_type"],
                status=s["status"],
                input_data=inp,
                output_data=out,
                error_message=s["error_message"],
                retry_count=s["retry_count"] or 0,
                tokens_used=s["tokens_used"] or 0,
                cost_usd=float(s["cost_usd"] or 0),
                duration_ms=s["duration_ms"],
                started_at=s["started_at"],
                completed_at=s["completed_at"],
            ))

        return ExecutionResponse(
            id=row["id"],
            workflow_id=row["workflow_id"],
            workflow_name=row.get("workflow_name") or "Workflow",
            status=row["status"],
            trigger_type=row["trigger_type"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            error_message=row["error_message"],
            total_tokens=row["total_tokens"] or 0,
            total_cost_usd=float(row["total_cost_usd"] or 0),
            metadata=meta or {},
            created_at=row["created_at"],
            steps=steps,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get execution")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{run_id}", status_code=200)
async def cancel_execution(run_id: UUID):
    """Cancel a running or pending execution."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE workflow_runs SET status = 'cancelled', completed_at = now()
                   WHERE id = $1 AND status IN ('pending', 'queued', 'running')""",
                run_id,
            )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Run not found or not cancellable")
        return {"detail": "Execution cancelled", "run_id": str(run_id)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to cancel execution")
        raise HTTPException(status_code=500, detail=str(exc))


@router.websocket("/ws/{run_id}")
async def execution_websocket(websocket: WebSocket, run_id: str):
    """Live stream execution events via WebSocket + Redis pub/sub."""
    await manager.connect(run_id, websocket)
    listen_task = asyncio.create_task(manager.listen_redis(run_id))
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        listen_task.cancel()
        manager.disconnect(run_id, websocket)
