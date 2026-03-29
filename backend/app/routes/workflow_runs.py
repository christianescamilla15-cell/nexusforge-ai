from fastapi import APIRouter, HTTPException
from ..metrics.collector import collector

router = APIRouter(prefix="/runs", tags=["Workflow Runs"])

@router.get("/")
async def list_runs(limit: int = 50):
    """List recent workflow runs."""
    runs = collector.get_runs(limit=limit)
    return {"runs": [r.model_dump() for r in runs], "total": len(runs)}

@router.get("/reliability/agents")
async def get_agent_reliability():
    """Get reliability scores for all agents."""
    from ..metrics.reliability import compute_agent_reliability
    scores = compute_agent_reliability()
    return {"agents": [vars(s) for s in scores]}

@router.get("/reliability/health")
async def get_system_health():
    """Get overall system health summary."""
    from ..metrics.reliability import get_system_health
    return get_system_health()

@router.get("/{run_id}")
async def get_run(run_id: str):
    """Get details for a specific run."""
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
    """Get unified timeline of all events for a run, ordered chronologically."""
    from ..metrics.collector import collector

    run = collector.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    timeline = []

    # Workflow start
    timeline.append({
        "timestamp": run.start_time.isoformat(),
        "type": "workflow",
        "event": "workflow_started",
        "step_id": None,
        "agent": None,
        "payload": {"workflow_name": run.workflow_name, "topology": run.topology},
    })

    # Steps
    for step in collector.get_steps(run_id):
        timeline.append({
            "timestamp": step.start_time.isoformat(),
            "type": "step",
            "event": f"step_{'completed' if step.status.value == 'completed' else step.status.value}",
            "step_id": step.id,
            "agent": step.agent_name,
            "payload": {"status": step.status.value, "latency_ms": step.latency_ms, "provider": step.provider_used},
        })

    # Events
    for event in collector.get_events(run_id):
        timeline.append({
            "timestamp": event.timestamp.isoformat(),
            "type": "event",
            "event": event.event_type.value,
            "step_id": None,
            "agent": event.agent_name,
            "payload": event.metadata,
        })

    # Workflow end
    if run.end_time:
        timeline.append({
            "timestamp": run.end_time.isoformat(),
            "type": "workflow",
            "event": f"workflow_{run.status.value}",
            "step_id": None,
            "agent": None,
            "payload": {"total_latency_ms": run.total_latency_ms},
        })

    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])

    return {"run_id": run_id, "timeline": timeline, "total_events": len(timeline)}
