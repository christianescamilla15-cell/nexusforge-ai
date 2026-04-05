"""Workflow runs — serves metrics from PostgreSQL workflow_runs (unified source of truth)."""

import json
import logging
from fastapi import APIRouter, HTTPException, Request
from ..metrics.collector import collector

router = APIRouter(prefix="/runs", tags=["Workflow Runs"])
logger = logging.getLogger(__name__)


def _get_user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    return uid


async def _get_db_runs(limit: int = 50, user_id: str = None) -> list:
    """Fetch runs from workflow_runs (unified source)."""
    try:
        from ..db.client import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            if user_id:
                rows = await conn.fetch(
                    """SELECT id, pipeline_name, status, trigger_type,
                              total_tokens, total_cost_usd, agents_used,
                              error_message, started_at, completed_at, metadata
                       FROM workflow_runs
                       WHERE user_id = $1::uuid OR user_id IS NULL
                       ORDER BY started_at DESC LIMIT $2""",
                    user_id, limit,
                )
            else:
                rows = await conn.fetch(
                    """SELECT id, pipeline_name, status, trigger_type,
                              total_tokens, total_cost_usd, agents_used,
                              error_message, started_at, completed_at, metadata
                       FROM workflow_runs ORDER BY started_at DESC LIMIT $1""",
                    limit,
                )
            runs = []
            for r in rows:
                agents = r["agents_used"]
                if isinstance(agents, str):
                    agents = json.loads(agents)
                meta = r["metadata"] or {}
                if isinstance(meta, str):
                    meta = json.loads(meta)

                # Compute latency from timestamps
                latency_ms = 0
                if r["completed_at"] and r["started_at"]:
                    latency_ms = int((r["completed_at"] - r["started_at"]).total_seconds() * 1000)

                workflow_name = (
                    r["pipeline_name"]
                    or meta.get("workflow_name")
                    or "workflow"
                )

                runs.append({
                    "id": str(r["id"]),
                    "workflow_name": workflow_name,
                    "pipeline_name": r["pipeline_name"],
                    "status": r["status"],
                    "trigger_source": r["trigger_type"],
                    "total_tokens": r["total_tokens"] or 0,
                    "tokens": r["total_tokens"] or 0,
                    "total_cost": float(r["total_cost_usd"] or 0),
                    "cost": float(r["total_cost_usd"] or 0),
                    "total_latency_ms": latency_ms,
                    "latency_ms": latency_ms,
                    "agents_used": agents if isinstance(agents, list) else [],
                    "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                    "finished_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                    "created_at": r["started_at"].isoformat() if r["started_at"] else None,
                    "notion_url": meta.get("notion_url"),
                    "error_message": r["error_message"],
                })
            return runs
    except Exception as e:
        logger.warning("Failed to fetch DB runs: %s", e)
        return []


async def _get_db_health(user_id: str = None) -> dict:
    """Compute system health from workflow_runs only (unified source)."""
    try:
        from ..db.client import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            user_filter = ""
            user_params: list = []
            if user_id:
                user_filter = "WHERE user_id = $1::uuid OR user_id IS NULL"
                user_params = [user_id]

            stats = await conn.fetchrow(f"""
                SELECT
                    COUNT(*) as total_runs,
                    COUNT(*) FILTER (WHERE status = 'completed') as successful,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(total_cost_usd), 0) as total_cost,
                    COALESCE(AVG(
                        EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000
                    ) FILTER (WHERE status = 'completed' AND completed_at IS NOT NULL), 0) as avg_latency,
                    COUNT(DISTINCT pipeline_name) as pipeline_count
                FROM workflow_runs {user_filter}
            """, *user_params)

            # Per-agent metrics from agents_used JSONB + step_executions
            agent_filter = "WHERE agents_used IS NOT NULL AND agents_used != '[]'::jsonb"
            if user_id:
                agent_filter += " AND (user_id = $1::uuid OR user_id IS NULL)"
            agent_rows = await conn.fetch(f"""
                SELECT agents_used, total_tokens, total_cost_usd,
                       EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000 as processing_time_ms,
                       status
                FROM workflow_runs {agent_filter}
            """, *user_params)

            # Retry/fallback counts from step_executions
            retry_rows = await conn.fetch("""
                SELECT agent_type,
                       COALESCE(SUM(retry_count), 0) as total_retries,
                       COUNT(*) FILTER (
                           WHERE output_data::text LIKE '%"_parse_failed": true%'
                              OR output_data::text LIKE '%"provider": "local"%'
                       ) as total_fallbacks
                FROM step_executions
                GROUP BY agent_type
            """)
            retry_map = {r["agent_type"]: r for r in retry_rows}

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
                    # Attach retry/fallback data from step_executions
                    rt = retry_map.get(a["agent"])
                    if rt:
                        a["retries"] = int(rt["total_retries"] or 0)
                        a["fallbacks"] = int(rt["total_fallbacks"] or 0)
                        a["retry_rate"] = round(a["retries"] / a["executions"], 3)
                del a["_total_latency"]
                del a["_successes"]
                agents.append(a)

            total = stats["total_runs"] or 0
            successful = stats["successful"] or 0
            failed = stats["failed"] or 0

            return {
                "status": "healthy" if total == 0 or (failed / max(total, 1) < 0.3) else "degraded",
                "total_runs": total,
                "successful_runs": successful,
                "failed_runs": failed,
                "system_success_rate": round(successful / max(total, 1), 3),
                "total_agents_tracked": int(stats.get("pipeline_count") or 0) or len(agents),
                "avg_latency_ms": round(float(stats["avg_latency"] or 0), 1),
                "total_tokens": int(stats["total_tokens"] or 0),
                "total_cost": round(float(stats["total_cost"] or 0), 6),
                "agents": sorted(agents, key=lambda x: x["executions"], reverse=True),
            }
    except Exception as e:
        logger.warning("Failed to compute DB health: %s", e)
        return None


@router.get("/")
async def list_runs(request: Request, limit: int = 50):
    """List recent runs — merges PostgreSQL workflow_runs + in-memory."""
    user_id = _get_user_id(request)
    db_runs = await _get_db_runs(limit, user_id=user_id)
    mem_runs = collector.get_runs(limit=limit)
    mem_list = [r.model_dump() for r in mem_runs]

    # Merge: DB runs first, then in-memory (avoid duplicates by id)
    db_ids = {r["id"] for r in db_runs}
    unique_mem = [r for r in mem_list if str(r.get("id", "")) not in db_ids]
    all_runs = db_runs + unique_mem
    source = "postgresql" if db_runs else ("memory" if mem_list else "empty")
    return {"runs": all_runs, "total": len(all_runs), "source": source}


@router.get("/reliability/agents")
async def get_agent_reliability():
    """Get reliability scores for all agents."""
    from ..metrics.reliability import compute_agent_reliability
    scores = compute_agent_reliability()
    return {"agents": [vars(s) for s in scores]}


@router.get("/reliability/health")
async def get_system_health(request: Request):
    """Get overall system health — reads from workflow_runs (unified source)."""
    user_id = _get_user_id(request)
    db_health = await _get_db_health(user_id=user_id)
    if db_health and db_health["total_runs"] > 0:
        return db_health

    from ..metrics.reliability import get_system_health
    return get_system_health()


@router.get("/{run_id}")
async def get_run(run_id: str, request: Request):
    """Get details for a specific run."""
    user_id = _get_user_id(request)
    # Try workflow_runs first
    try:
        from ..db.client import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            import uuid
            row = await conn.fetchrow(
                "SELECT * FROM workflow_runs WHERE id = $1 AND (user_id = $2::uuid OR user_id IS NULL)",
                uuid.UUID(run_id), user_id,
            )
            if row:
                agents = row["agents_used"]
                if isinstance(agents, str):
                    agents = json.loads(agents)
                meta = row["metadata"] or {}
                if isinstance(meta, str):
                    meta = json.loads(meta)
                latency_ms = 0
                if row["completed_at"] and row["started_at"]:
                    latency_ms = int((row["completed_at"] - row["started_at"]).total_seconds() * 1000)
                return {
                    "id": str(row["id"]),
                    "workflow_name": row["pipeline_name"] or meta.get("workflow_name", "workflow"),
                    "pipeline_name": row["pipeline_name"],
                    "status": row["status"],
                    "total_tokens": row["total_tokens"] or 0,
                    "total_cost": float(row["total_cost_usd"] or 0),
                    "total_latency_ms": latency_ms,
                    "agents_used": agents if isinstance(agents, list) else [],
                    "notion_url": meta.get("notion_url"),
                    "started_at": row["started_at"].isoformat() if row["started_at"] else None,
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
