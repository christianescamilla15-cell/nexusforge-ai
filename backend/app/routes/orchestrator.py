"""Orchestrator API — Claude reads/writes agent memories and documents sessions."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.memory.orchestrator import get_orchestrator_memory

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class InjectRequest(BaseModel):
    agent_id: str
    knowledge: str
    source: str = "orchestrator"
    tier: str = "episodic"

class BroadcastRequest(BaseModel):
    knowledge: str
    source: str = "orchestrator"

class SessionDocument(BaseModel):
    title: str
    summary: str
    decisions: list[str] = []
    agents_involved: list[str] = []


# ── Read endpoints ────────────────────────────────────────────────────────────

@router.get("/snapshot")
async def get_system_snapshot(limit_per_agent: int = 5):
    """Full memory snapshot of all agents — orchestrator's system view."""
    mem = get_orchestrator_memory()
    snapshot = await mem.read_all_agents(limit_per_agent=limit_per_agent)
    return {"agents": snapshot, "total_agents_with_memory": len(snapshot)}


@router.get("/agent/{agent_id}")
async def get_agent_profile(agent_id: str):
    """Full profile for a specific agent: episodes, patterns, stats, semantic memories."""
    mem = get_orchestrator_memory()
    profile = await mem.get_agent_profile(agent_id)
    return profile


@router.get("/feed")
async def get_experience_feed(limit: int = 50):
    """Chronological experience feed across all agents — most recent first."""
    mem = get_orchestrator_memory()
    feed = await mem.get_experience_feed(limit=limit)
    return {"feed": feed, "count": len(feed)}


@router.get("/log")
async def get_orchestrator_log(limit: int = 20):
    """Orchestrator's own session documents and decisions."""
    mem = get_orchestrator_memory()
    log = await mem.get_orchestrator_log(limit=limit)
    return {"log": log, "count": len(log)}


# ── Write endpoints ───────────────────────────────────────────────────────────

@router.post("/inject")
async def inject_context(req: InjectRequest):
    """Inject knowledge into a specific agent's memory."""
    mem = get_orchestrator_memory()
    ok = await mem.inject_context(
        agent_id=req.agent_id,
        knowledge=req.knowledge,
        source=req.source,
        tier=req.tier,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to inject context")
    return {"status": "injected", "agent_id": req.agent_id, "tier": req.tier}


@router.post("/broadcast")
async def broadcast_context(req: BroadcastRequest):
    """Broadcast knowledge to ALL agents at once."""
    mem = get_orchestrator_memory()
    results = await mem.inject_to_all(req.knowledge, source=req.source)
    success = sum(1 for v in results.values() if v)
    return {"status": "broadcast", "injected": success, "total": len(results), "results": results}


@router.post("/document")
async def document_session(doc: SessionDocument):
    """Record an orchestrator session note for future recall."""
    mem = get_orchestrator_memory()
    ok = await mem.document_session(
        title=doc.title,
        summary=doc.summary,
        decisions=doc.decisions,
        agents_involved=doc.agents_involved,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to document session")
    return {"status": "documented", "title": doc.title}
