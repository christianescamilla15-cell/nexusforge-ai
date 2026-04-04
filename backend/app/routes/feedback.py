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

class FeedbackInput(BaseModel):
    run_id: str
    rating: int = 3
    approved: bool = False
    comments: str = ""
    reviewer: str = "anonymous"
    agent_type: str = ""
    workflow_type: str = ""

@router.post("/submit")
async def submit_run_feedback(fb: FeedbackInput):
    # Validate UUID format
    import uuid as _uuid
    try:
        _uuid.UUID(fb.run_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid run_id format — must be a valid UUID")

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
                """INSERT INTO run_feedback (run_id, rating, approved, comments, agent_type, workflow_type)
                   VALUES ($1::uuid, $2, $3, $4, $5, $6)""",
                fb.run_id, fb.rating, fb.approved, fb.comments, fb.agent_type, fb.workflow_type,
            )
    except Exception as exc:
        logger.warning("Feedback DB persist failed (in-memory still saved): %s", exc)
    return result.model_dump()

@router.get("/run/{run_id}")
async def get_run_feedback(run_id: str):
    feedback = get_feedback_for_run(run_id)
    return {"feedback": [f.model_dump() for f in feedback]}

@router.get("/all")
async def list_all_feedback(limit: int = 50):
    feedback = get_all_feedback(limit=limit)
    return {"feedback": [f.model_dump() for f in feedback], "total": len(feedback)}

@router.get("/stats")
async def feedback_stats():
    return get_feedback_stats()

@router.get("/agents/performance")
async def agent_performance(agent_name: str = None):
    agents = get_agent_performance(agent_name)
    return {"agents": [a.model_dump() for a in agents]}

@router.get("/agents/top")
async def top_agents(n: int = 5):
    agents = get_top_agents(n)
    return {"top_agents": [a.model_dump() for a in agents]}

@router.get("/agents/recommendations")
async def agent_recommendations(workflow: str = ""):
    return get_agent_recommendations(workflow)

@router.post("/refresh")
async def refresh_performance():
    refresh_agent_performance()
    agents = get_agent_performance()
    return {"status": "refreshed", "agents_computed": len(agents)}
