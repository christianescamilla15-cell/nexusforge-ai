"""Custom agents — user-defined AI agents with custom prompts."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..auth.jwt_handler import verify_token
from ..auth.audit import log_action
from ..db.client import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/custom-agents", tags=["Custom Agents"])


class CreateAgentRequest(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    model: str = "llama-3.3-70b-versatile"
    provider: str = "groq"
    temperature: float = 0.3
    max_tokens: int = 1024
    is_public: bool = False


class ExecuteAgentRequest(BaseModel):
    input: str
    context: Optional[str] = None


def _get_user_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")
    return token_data["sub"]


@router.post("/")
async def create_agent(req: CreateAgentRequest, request: Request):
    """Create a custom agent."""
    user_id = _get_user_id(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Limit: max 10 custom agents per user
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM custom_agents WHERE user_id = $1::uuid",
            user_id,
        )
        if count >= 10:
            raise HTTPException(400, "Maximum 10 custom agents per account")

        row = await conn.fetchrow(
            """INSERT INTO custom_agents (user_id, name, description, system_prompt,
               model, provider, temperature, max_tokens, is_public)
               VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id""",
            user_id, req.name, req.description, req.system_prompt,
            req.model, req.provider, req.temperature, req.max_tokens, req.is_public,
        )

    await log_action(user_id, "agent.create", "custom_agent", str(row["id"]),
                      {"name": req.name, "model": req.model})

    return {"id": str(row["id"]), "name": req.name, "created": True}


@router.get("/")
async def list_agents(request: Request):
    """List user's custom agents + public agents."""
    user_id = _get_user_id(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, name, description, agent_type, model, provider,
                      temperature, max_tokens, is_public, executions, created_at
               FROM custom_agents
               WHERE user_id = $1::uuid OR is_public = true
               ORDER BY created_at DESC""",
            user_id,
        )

    return {
        "agents": [{
            "id": str(r["id"]),
            "name": r["name"],
            "description": r["description"],
            "model": r["model"],
            "provider": r["provider"],
            "temperature": float(r["temperature"]),
            "max_tokens": r["max_tokens"],
            "is_public": r["is_public"],
            "executions": r["executions"],
        } for r in rows]
    }


@router.post("/{agent_id}/execute")
async def execute_agent(agent_id: str, req: ExecuteAgentRequest, request: Request):
    """Execute a custom agent."""
    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)
    user_id = _get_user_id(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        agent = await conn.fetchrow(
            """SELECT * FROM custom_agents
               WHERE id = $1::uuid AND (user_id = $2::uuid OR is_public = true)""",
            agent_id, user_id,
        )

    if not agent:
        raise HTTPException(404, "Agent not found")

    # Execute via LLM
    import time
    start = time.time()

    try:
        from ..llm.router import route_llm_call
        response = await route_llm_call(
            system_prompt=agent["system_prompt"],
            user_message=req.input,
            context=req.context,
            model=agent["model"],
            provider=agent["provider"],
            temperature=float(agent["temperature"]),
            max_tokens=agent["max_tokens"],
        )
        output = response.content
        tokens = response.tokens_input + response.tokens_output
        cost = response.cost_usd
        provider_used = response.provider
    except Exception:
        # Fallback to demo response
        output = f"[{agent['name']}] Processed: {req.input[:100]}"
        tokens = int(len(req.input) / 4) + 100
        cost = tokens * 0.0000006
        provider_used = "demo"

    duration = int((time.time() - start) * 1000)

    # Update execution count
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE custom_agents SET executions = executions + 1 WHERE id = $1::uuid",
            agent_id,
        )

    await log_action(user_id, "agent.execute", "custom_agent", agent_id,
                      {"name": agent["name"], "input_length": len(req.input)},
                      tokens_used=tokens, cost_usd=cost, duration_ms=duration)

    return {
        "output": output,
        "agent": agent["name"],
        "provider": provider_used,
        "tokens": tokens,
        "cost_usd": cost,
        "duration_ms": duration,
    }


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, request: Request):
    """Delete a custom agent."""
    user_id = _get_user_id(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM custom_agents WHERE id = $1::uuid AND user_id = $2::uuid",
            agent_id, user_id,
        )

    await log_action(user_id, "agent.delete", "custom_agent", agent_id)
    return {"deleted": True}
