"""API routes for MongoDB-backed episodic memory (polyglot persistence)."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any

from app.memory.episodic_mongo import MongoEpisodicMemory

router = APIRouter()
_mongo_memory = MongoEpisodicMemory()


class StoreEpisodeRequest(BaseModel):
    agent_id: str
    episode_type: str
    summary: str
    context: dict[str, Any] = Field(default_factory=dict)
    outcome: str = "success"


@router.get("/memory/episodes/{agent_id}")
async def get_episodes(agent_id: str, limit: int = 10):
    """Get episodic memory for an agent from MongoDB."""
    episodes = await _mongo_memory.recall_recent(agent_id, limit=limit)
    return {"agent_id": agent_id, "count": len(episodes), "episodes": episodes}


@router.get("/memory/patterns/{agent_id}")
async def get_patterns(agent_id: str):
    """Get success/failure patterns from MongoDB aggregation."""
    patterns = await _mongo_memory.get_patterns(agent_id)
    return {"agent_id": agent_id, **patterns}


@router.get("/memory/stats/{agent_id}")
async def get_stats(agent_id: str):
    """Get agent episode statistics."""
    stats = await _mongo_memory.get_agent_stats(agent_id)
    return {"agent_id": agent_id, **stats}


@router.post("/memory/episodes")
async def store_episode(body: StoreEpisodeRequest):
    """Store a new episode in MongoDB."""
    episode_id = await _mongo_memory.store_episode(
        agent_id=body.agent_id,
        episode_type=body.episode_type,
        summary=body.summary,
        context=body.context,
        outcome=body.outcome,
    )
    return {
        "stored": episode_id is not None,
        "episode_id": episode_id,
        "agent_id": body.agent_id,
    }
