import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from ..services.feedback_service import (
    submit_feedback, get_feedback_for_run, get_all_feedback,
    get_feedback_stats, get_agent_performance, get_top_agents,
    get_agent_recommendations, refresh_agent_performance,
)
from ..db.client import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["Feedback Loop"])


def _get_user_id(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise HTTPException(status_code=401, detail="Login required")
    return uid

class FeedbackInput(BaseModel):
    run_id: str
    rating: int = 3
    approved: bool = False
    comments: str = ""
    reviewer: str = "anonymous"
    agent_type: str = ""
    workflow_type: str = ""

@router.post("/submit")  # mythos: public — anonymous feedback intentional (run_id is the auth boundary)
async def submit_run_feedback(fb: FeedbackInput, request: Request):
    # Validate UUID format
    import uuid as _uuid
    try:
        _uuid.UUID(fb.run_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid run_id format — must be a valid UUID")

    # Get user_id if available (submit allows anonymous)
    user_id = getattr(request.state, "user_id", None)

    # In-memory (backwards compat)
    result = submit_feedback(
        run_id=fb.run_id, rating=fb.rating, approved=fb.approved,
        comments=fb.comments, reviewer=fb.reviewer,
    )
    # Persist to DB (survives restart)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO run_feedback (run_id, rating, approved, comments, agent_type, workflow_type, user_id)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6, $7::uuid)""",
                fb.run_id, fb.rating, fb.approved, fb.comments, fb.agent_type, fb.workflow_type, user_id,
            )
    except Exception as exc:
        logger.warning("Feedback DB persist failed (in-memory still saved): %s", exc)
    return result.model_dump()

@router.get("/run/{run_id}")
async def get_run_feedback(run_id: str, request: Request):
    _get_user_id(request)
    feedback = get_feedback_for_run(run_id)
    return {"feedback": [f.model_dump() for f in feedback]}

@router.get("/all")
async def list_all_feedback(request: Request, limit: int = 50):
    _get_user_id(request)
    feedback = get_all_feedback(limit=limit)
    return {"feedback": [f.model_dump() for f in feedback], "total": len(feedback)}

@router.get("/stats")
async def feedback_stats(request: Request):
    _get_user_id(request)
    return get_feedback_stats()

@router.get("/agents/performance")
async def agent_performance(request: Request, agent_name: str = None):
    _get_user_id(request)
    agents = get_agent_performance(agent_name)
    return {"agents": [a.model_dump() for a in agents]}

@router.get("/agents/top")
async def top_agents(request: Request, n: int = 5):
    _get_user_id(request)
    agents = get_top_agents(n)
    return {"top_agents": [a.model_dump() for a in agents]}

@router.get("/agents/recommendations")
async def agent_recommendations(request: Request, workflow: str = ""):
    _get_user_id(request)
    return get_agent_recommendations(workflow)

@router.post("/refresh")
async def refresh_performance(request: Request):
    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)
    _get_user_id(request)
    refresh_agent_performance()
    agents = get_agent_performance()
    return {"status": "refreshed", "agents_computed": len(agents)}
