"""Swarm topology API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.swarms.manager import get_swarm, list_topologies

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

    return SwarmResultResponse(
        output=result.output,
        topology=result.topology,
        agents_used=result.agents_used,
        total_tokens=result.total_tokens,
        total_cost=result.total_cost,
        steps_executed=result.steps_executed,
        duration_ms=result.duration_ms,
    )
