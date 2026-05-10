"""Orchestrator API — Claude reads/writes agent memories and documents sessions.

Admin-only by design: every endpoint here either reads cross-agent
memory (operator-level visibility) or mutates agent memory state
(write-level access). Mirrors the admin.py pattern: `_require_admin`
returns 404 (not 403) so route presence isn't disclosed to non-admins.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.memory.orchestrator import get_orchestrator_memory

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


def _require_admin(request: Request) -> dict:
    """Admin-only guard. Mirrors admin.py pattern (404 not 403)."""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(404, "Not found")
    return user


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
async def get_system_snapshot(request: Request, limit_per_agent: int = 5):
    """Full memory snapshot of all agents — orchestrator's system view."""
    _require_admin(request)
    mem = get_orchestrator_memory()
    snapshot = await mem.read_all_agents(limit_per_agent=limit_per_agent)
    return {"agents": snapshot, "total_agents_with_memory": len(snapshot)}


@router.get("/agent/{agent_id}")
async def get_agent_profile(agent_id: str, request: Request):
    """Full profile for a specific agent: episodes, patterns, stats, semantic memories."""
    _require_admin(request)
    mem = get_orchestrator_memory()
    profile = await mem.get_agent_profile(agent_id)
    return profile


@router.get("/feed")
async def get_experience_feed(request: Request, limit: int = 50):
    """Chronological experience feed across all agents — most recent first."""
    _require_admin(request)
    mem = get_orchestrator_memory()
    feed = await mem.get_experience_feed(limit=limit)
    return {"feed": feed, "count": len(feed)}


@router.get("/log")
async def get_orchestrator_log(request: Request, limit: int = 20):
    """Orchestrator's own session documents and decisions."""
    _require_admin(request)
    mem = get_orchestrator_memory()
    log = await mem.get_orchestrator_log(limit=limit)
    return {"log": log, "count": len(log)}


# ── Write endpoints ───────────────────────────────────────────────────────────

@router.post("/inject")
async def inject_context(req: InjectRequest, request: Request):
    """Inject knowledge into a specific agent's memory."""
    _require_admin(request)
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
async def broadcast_context(req: BroadcastRequest, request: Request):
    """Broadcast knowledge to ALL agents at once."""
    _require_admin(request)
    mem = get_orchestrator_memory()
    results = await mem.inject_to_all(req.knowledge, source=req.source)
    success = sum(1 for v in results.values() if v)
    return {"status": "broadcast", "injected": success, "total": len(results), "results": results}


@router.post("/document")
async def document_session(doc: SessionDocument, request: Request):
    """Record an orchestrator session note for future recall."""
    _require_admin(request)
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
