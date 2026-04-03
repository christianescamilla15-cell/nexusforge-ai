"""Swarm topology API routes."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.swarms.manager import get_swarm, list_topologies
from app.db.client import get_db_pool
from app.db.pipeline_store import save_pipeline_run
from app.integrations.email.notify import notify_workflow_complete
from app.utils.run_tracker import start_run, record_step, complete_run

logger = logging.getLogger(__name__)

router = APIRouter()


class SwarmExecuteRequest(BaseModel):
    topology: str
    agent_types: list[str]
    input_data: dict = {}
    config: dict = {}


class SwarmResultResponse(BaseModel):
    output: dict
    topology: str
    agents_used: list[str]
    total_tokens: int
    total_cost: float
    steps_executed: int
    duration_ms: int


@router.get("/")
async def get_topologies():
    """List all available swarm topologies."""
    return {"topologies": list_topologies()}


@router.post("/execute", response_model=SwarmResultResponse)
async def execute_swarm(req: SwarmExecuteRequest):
    """Execute a swarm with given agents and input."""
    try:
        swarm = get_swarm(req.topology)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not req.agent_types:
        raise HTTPException(status_code=400, detail="agent_types must not be empty")

    try:
        result = await swarm.execute(
            input_data=req.input_data,
            agent_types=req.agent_types,
            config=req.config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Swarm execution failed: {e}")

    # Persist to DB
    try:
        pool = await get_db_pool()
        if pool:
            await save_pipeline_run(
                pool,
                pipeline_name=f"swarm_{req.topology}",
                status="completed",
                trigger_source="backend",
                total_tokens=result.total_tokens,
                cost_usd=result.total_cost,
                processing_time_ms=result.duration_ms,
                agents_used=result.agents_used,
                steps=[f"{a}: completed" for a in result.agents_used],
            )
    except Exception as e:
        logger.warning("Failed to persist swarm run: %s", e)

    # Email notification
    await notify_workflow_complete(
        workflow_name=f"Swarm ({req.topology})",
        status="completed",
        summary=f"{req.topology} topology with {len(result.agents_used)} agents, {result.steps_executed} steps",
        agents_used=result.agents_used,
        total_tokens=result.total_tokens,
        cost_usd=result.total_cost,
        processing_time_ms=result.duration_ms,
        extra_details={"topology": req.topology, "steps_executed": result.steps_executed},
    )

    # Track in workflow_runs for Executions page
    try:
        task_str = str(req.input_data.get("task", ""))[:100] if req.input_data else ""
        tracker_id = await start_run(f"Swarm ({req.topology})", metadata={"topology": req.topology, "task": task_str})
        agents = result.agents_used or []
        for agent in agents:
            await record_step(tracker_id, agent, agent.lower().replace("agent", ""), tokens_used=result.total_tokens // max(len(agents), 1), cost_usd=result.total_cost / max(len(agents), 1), duration_ms=result.duration_ms // max(len(agents), 1))
        await complete_run(tracker_id, total_tokens=result.total_tokens, total_cost_usd=result.total_cost)
    except Exception as e:
        logger.warning("swarms: run_tracker failed: %s", e)

    return SwarmResultResponse(
        output=result.output,
        topology=result.topology,
        agents_used=result.agents_used,
        total_tokens=result.total_tokens,
        total_cost=result.total_cost,
        steps_executed=result.steps_executed,
        duration_ms=result.duration_ms,
    )
