"""Swarm topology API routes."""

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.swarms.manager import get_swarm, list_topologies
from app.integrations.email.notify import notify_workflow_complete
from app.utils.run_tracker import start_run, record_step, complete_run

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_user_id(request: Request) -> str:
    """Extract and verify user from JWT. Raises 401 if missing/invalid."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return token_data["sub"]


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
async def execute_swarm(req: SwarmExecuteRequest, request: Request):
    """Execute a swarm with given agents and input."""
    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)
    _get_user_id(request)  # require auth
    try:
        swarm = get_swarm(req.topology)
    except ValueError:
        logger.info("Swarm execute: unknown topology %r", req.topology)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown swarm topology: {req.topology!r}",
        )

    if not req.agent_types:
        raise HTTPException(status_code=400, detail="agent_types must not be empty")

    try:
        result = await swarm.execute(
            input_data=req.input_data,
            agent_types=req.agent_types,
            config=req.config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Swarm execution failed")

    # Persist to workflow_runs via run_tracker (unified source)
    try:
        task_str = str(req.input_data.get("task", ""))[:100] if req.input_data else ""
        tracker_id = await start_run(
            pipeline_name=f"swarm_{req.topology}",
            trigger_type="api",
            metadata={"topology": req.topology, "task": task_str},
        )
        agents = result.agents_used or []
        agent_count = max(len(agents), 1)
        for agent in agents:
            await record_step(
                tracker_id, agent, agent.lower().replace("agent", ""),
                tokens_used=result.total_tokens // agent_count,
                cost_usd=result.total_cost / agent_count,
                duration_ms=result.duration_ms // agent_count,
            )
        await complete_run(
            tracker_id,
            total_tokens=result.total_tokens,
            total_cost_usd=result.total_cost,
            agents_used=result.agents_used,
        )
    except Exception as e:
        logger.warning("swarms: run_tracker failed: %s", e)

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
