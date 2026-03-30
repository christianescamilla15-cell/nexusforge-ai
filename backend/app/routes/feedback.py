from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..services.feedback_service import (
    submit_feedback, get_feedback_for_run, get_all_feedback,
    get_feedback_stats, get_agent_performance, get_top_agents,
    get_agent_recommendations, refresh_agent_performance,
)

router = APIRouter(prefix="/feedback", tags=["Feedback Loop"])

class FeedbackInput(BaseModel):
    run_id: str
    rating: int = 3
    approved: bool = False
    comments: str = ""
    reviewer: str = "anonymous"

@router.post("/submit")
async def submit_run_feedback(fb: FeedbackInput):
    result = submit_feedback(
        run_id=fb.run_id, rating=fb.rating, approved=fb.approved,
        comments=fb.comments, reviewer=fb.reviewer,
    )
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
