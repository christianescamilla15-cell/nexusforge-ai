"""Workflow runs — serves metrics from PostgreSQL pipeline_runs + in-memory collector."""

import json
import logging
import os
from fastapi import APIRouter, HTTPException
from ..metrics.collector import collector

router = APIRouter(prefix="/runs", tags=["Workflow Runs"])
logger = logging.getLogger(__name__)


async def _get_db_runs(limit: int = 50) -> list:
    """Fetch pipeline runs from PostgreSQL."""
    try:
        from ..db.client import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, pipeline_name, status, trigger_source, file_name,
                          document_type, total_tokens, cost_usd, processing_time_ms,
                          llm_used, agents_used, steps, notion_url, error_message, created_at
                   FROM pipeline_runs ORDER BY created_at DESC LIMIT $1""",
                limit,
            )
            runs = []
            for r in rows:
                agents = r["agents_used"]
                if isinstance(agents, str):
                    agents = json.loads(agents)
                runs.append({
                    "id": str(r["id"]),
                    "workflow_name": r["pipeline_name"] or "pipeline",
                    "status": r["status"],
                    "trigger_source": r["trigger_source"],
                    "file_name": r["file_name"],
                    "document_type": r["document_type"],
                    "total_tokens": r["total_tokens"] or 0,
                    "tokens": r["total_tokens"] or 0,
                    "total_cost": float(r["cost_usd"] or 0),
                    "cost": float(r["cost_usd"] or 0),
                    "total_latency_ms": r["processing_time_ms"] or 0,
                    "latency_ms": r["processing_time_ms"] or 0,
                    "agents_used": agents if isinstance(agents, list) else [],
                    "started_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "finished_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "notion_url": r["notion_url"],
                    "error_message": r["error_message"],
                })
            return runs
    except Exception as e:
        logger.warning("Failed to fetch DB runs: %s", e)
        return []


async def _get_db_health() -> dict:
    """Compute system health from PostgreSQL pipeline_runs."""
    try:
        from ..db.client import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_runs,
                    COUNT(*) FILTER (WHERE status = 'completed') as successful,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(cost_usd), 0) as total_cost,
                    COALESCE(AVG(processing_time_ms), 0) as avg_latency
                FROM pipeline_runs
            """)

            agent_rows = await conn.fetch("""
                SELECT agents_used, total_tokens, cost_usd, processing_time_ms, status
                FROM pipeline_runs WHERE agents_used IS NOT NULL
            """)

            # Aggregate per-agent metrics
            agent_map = {}
            for row in agent_rows:
                agents = row["agents_used"]
                if isinstance(agents, str):
                    agents = json.loads(agents)
                if not isinstance(agents, list):
                    continue
                for agent_name in agents:
                    if agent_name not in agent_map:
                        agent_map[agent_name] = {
                            "agent": agent_name,
                            "executions": 0,
                            "success_rate": 0,
                            "avg_latency_ms": 0,
                            "tokens": 0,
                            "retries": 0,
                            "fallbacks": 0,
                            "retry_rate": 0,
                            "_total_latency": 0,
                            "_successes": 0,
                        }
                    a = agent_map[agent_name]
                    a["executions"] += 1
                    a["tokens"] += row["total_tokens"] or 0
                    a["_total_latency"] += row["processing_time_ms"] or 0
                    if row["status"] == "completed":
                        a["_successes"] += 1

            agents = []
            for a in agent_map.values():
                if a["executions"] > 0:
                    a["avg_latency_ms"] = round(a["_total_latency"] / a["executions"], 1)
                    a["success_rate"] = round(a["_successes"] / a["executions"], 2)
                del a["_total_latency"]
                del a["_successes"]
                agents.append(a)

            total = stats["total_runs"] or 0
            successful = stats["successful"] or 0
            failed = stats["failed"] or 0

            return {
                "status": "healthy" if total > 0 and failed / max(total, 1) < 0.3 else "degraded",
                "total_runs": total,
                "successful_runs": successful,
                "failed_runs": failed,
                "system_success_rate": round(successful / max(total, 1), 3),
                "total_agents_tracked": len(agents),
                "avg_latency_ms": round(float(stats["avg_latency"] or 0), 1),
                "total_tokens": int(stats["total_tokens"] or 0),
                "total_cost": round(float(stats["total_cost"] or 0), 6),
                "agents": sorted(agents, key=lambda x: x["executions"], reverse=True),
            }
    except Exception as e:
        logger.warning("Failed to compute DB health: %s", e)
        return None


@router.get("/")
async def list_runs(limit: int = 50):
    """List recent runs — merges PostgreSQL + in-memory."""
    db_runs = await _get_db_runs(limit)
    mem_runs = collector.get_runs(limit=limit)
    mem_list = [r.model_dump() for r in mem_runs]

    # Merge: DB runs first, then in-memory (avoid duplicates)
    all_runs = db_runs + mem_list
    source = "postgresql" if db_runs else ("memory" if mem_list else "empty")
    return {"runs": all_runs, "total": len(all_runs), "source": source}


@router.get("/reliability/agents")
async def get_agent_reliability():
    """Get reliability scores for all agents."""
    from ..metrics.reliability import compute_agent_reliability
    scores = compute_agent_reliability()
    return {"agents": [vars(s) for s in scores]}


@router.get("/reliability/health")
async def get_system_health():
    """Get overall system health — tries PostgreSQL first."""
    db_health = await _get_db_health()
    if db_health and db_health["total_runs"] > 0:
        return db_health

    from ..metrics.reliability import get_system_health
    return get_system_health()


@router.get("/{run_id}")
async def get_run(run_id: str):
    """Get details for a specific run."""
    # Try DB first
    try:
        from ..db.client import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            import uuid
            row = await conn.fetchrow(
                "SELECT * FROM pipeline_runs WHERE id = $1",
                uuid.UUID(run_id),
            )
            if row:
                agents = row["agents_used"]
                if isinstance(agents, str):
                    agents = json.loads(agents)
                steps = row["steps"]
                if isinstance(steps, str):
                    steps = json.loads(steps)
                return {
                    "id": str(row["id"]),
                    "workflow_name": row["pipeline_name"],
                    "status": row["status"],
                    "file_name": row["file_name"],
                    "document_type": row["document_type"],
                    "total_tokens": row["total_tokens"] or 0,
                    "total_cost": float(row["cost_usd"] or 0),
                    "total_latency_ms": row["processing_time_ms"] or 0,
                    "agents_used": agents if isinstance(agents, list) else [],
                    "steps": steps if isinstance(steps, list) else [],
                    "notion_url": row["notion_url"],
                    "started_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
    except Exception:
        pass

    run = collector.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run.model_dump()


@router.get("/{run_id}/steps")
async def get_run_steps(run_id: str):
    """Get all steps for a specific run."""
    steps = collector.get_steps(run_id)
    return {"steps": [s.model_dump() for s in steps], "total": len(steps)}


@router.get("/{run_id}/events")
async def get_run_events(run_id: str):
    """Get all events for a specific run."""
    events = collector.get_events(run_id)
    return {"events": [e.model_dump() for e in events], "total": len(events)}


@router.get("/{run_id}/metrics")
async def get_run_metrics(run_id: str):
    """Get aggregated metrics for a specific run."""
    metrics = collector.get_metrics(run_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Run not found")
    return metrics.model_dump()


@router.get("/{run_id}/timeline")
async def get_run_timeline(run_id: str):
    """Get unified timeline of all events for a run."""
    run = collector.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    timeline = []
    timeline.append({
        "timestamp": run.start_time.isoformat(),
        "type": "workflow",
        "event": "workflow_started",
        "step_id": None,
        "agent": None,
        "payload": {"workflow_name": run.workflow_name, "topology": run.topology},
    })

    for step in collector.get_steps(run_id):
        timeline.append({
            "timestamp": step.start_time.isoformat(),
            "type": "step",
            "event": f"step_{'completed' if step.status.value == 'completed' else step.status.value}",
            "step_id": step.id,
            "agent": step.agent_name,
            "payload": {"status": step.status.value, "latency_ms": step.latency_ms, "provider": step.provider_used},
        })

    for event in collector.get_events(run_id):
        timeline.append({
            "timestamp": event.timestamp.isoformat(),
            "type": "event",
            "event": event.event_type.value,
            "step_id": None,
            "agent": event.agent_name,
            "payload": event.metadata,
        })

    if run.end_time:
        timeline.append({
            "timestamp": run.end_time.isoformat(),
            "type": "workflow",
            "event": f"workflow_{run.status.value}",
            "step_id": None,
            "agent": None,
            "payload": {"total_latency_ms": run.total_latency_ms},
        })

    timeline.sort(key=lambda x: x["timestamp"])
    return {"run_id": run_id, "timeline": timeline, "total_events": len(timeline)}
