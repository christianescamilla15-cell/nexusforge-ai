"""Swarm topology API routes."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.swarms.manager import get_swarm, list_topologies
from app.db.client import get_db_pool
from app.db.pipeline_store import save_pipeline_run
from app.integrations.email.notify import notify_workflow_complete

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
                trigger_source="frontend",
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

    return SwarmResultResponse(
        output=result.output,
        topology=result.topology,
        agents_used=result.agents_used,
        total_tokens=result.total_tokens,
        total_cost=result.total_cost,
        steps_executed=result.steps_executed,
        duration_ms=result.duration_ms,
    )
