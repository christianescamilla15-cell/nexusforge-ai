from fastapi import APIRouter, HTTPException
from ..metrics.collector import collector

router = APIRouter(prefix="/runs", tags=["Workflow Runs"])

@router.get("/")
async def list_runs(limit: int = 50):
    """List recent workflow runs."""
    runs = collector.get_runs(limit=limit)
    return {"runs": [r.model_dump() for r in runs], "total": len(runs)}

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
