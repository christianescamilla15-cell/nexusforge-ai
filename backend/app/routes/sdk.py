"""Agent SDK endpoints — exposes Claude Agent SDK capabilities via REST API.

Provides:
- /sdk/run — Execute any task via Agent SDK with sub-agents
- /sdk/review — Code review with security sub-agent
- /sdk/research — Web research with search tools
- /sdk/batch — Submit batch of tasks for async processing
- /sdk/health — Check SDK availability
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sdk", tags=["agent-sdk"])


class SDKRunRequest(BaseModel):
    prompt: str
    tools: list[str] | None = None
    agents: dict | None = None
    resume_session: bool = False
    effort: str = "medium"  # low, medium, high, max


class SDKBatchRequest(BaseModel):
    tasks: list[dict]  # [{prompt, tools?, agents?}, ...]


def _get_user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user.get("sub", user.get("user_id", ""))


@router.get("/health")
async def sdk_health():
    """Check Agent SDK and Claude API availability."""
    from app.meta.agent_sdk_bridge import get_sdk_bridge
    bridge = get_sdk_bridge()
    return {
        "agent_sdk": "available" if bridge.available else "not configured",
        "features": {
            "sub_agents": bridge.available,
            "hooks": bridge.available,
            "sessions": bridge.available,
            "prompt_caching": True,
            "batch_api": True,
            "adaptive_thinking": True,
        },
    }


@router.post("/run")
async def sdk_run(body: SDKRunRequest, request: Request):
    """Run a task through the Claude Agent SDK."""
    _get_user_id(request)

    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)

    from app.meta.agent_sdk_bridge import get_sdk_bridge
    bridge = get_sdk_bridge()
    if not bridge.available:
        raise HTTPException(status_code=503, detail="Agent SDK not available. Set ANTHROPIC_API_KEY.")

    result = await bridge.run(
        prompt=body.prompt,
        tools=body.tools,
        agents=body.agents,
        resume_session=body.resume_session,
    )
    return result


@router.post("/review")
async def sdk_review(body: dict, request: Request):
    """Code review with security sub-agent."""
    _get_user_id(request)
    from app.meta.agent_sdk_bridge import get_sdk_bridge
    bridge = get_sdk_bridge()
    if not bridge.available:
        raise HTTPException(status_code=503, detail="Agent SDK not available")
    return await bridge.code_review(body.get("file_path", ""))


@router.post("/research")
async def sdk_research(body: dict, request: Request):
    """Web research on a topic."""
    _get_user_id(request)
    from app.meta.agent_sdk_bridge import get_sdk_bridge
    bridge = get_sdk_bridge()
    if not bridge.available:
        raise HTTPException(status_code=503, detail="Agent SDK not available")
    return await bridge.research(body.get("topic", ""))


@router.post("/batch")
async def sdk_batch(body: SDKBatchRequest, request: Request):
    """Submit batch of tasks for async processing (50% cost savings)."""
    _get_user_id(request)

    from app.meta.agent_sdk_bridge import get_sdk_bridge
    bridge = get_sdk_bridge()

    # Use Anthropic Batch API directly for cost savings
    try:
        import anthropic
        from app.config import settings

        if not settings.anthropic_api_key:
            raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not set")

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        requests = []
        for i, task in enumerate(body.tasks):
            requests.append({
                "custom_id": f"task-{i}",
                "params": {
                    "model": "claude-sonnet-4-6",
                    "max_tokens": task.get("max_tokens", 2048),
                    "messages": [{"role": "user", "content": task["prompt"]}],
                },
            })

        batch = client.messages.batches.create(requests=requests)
        return {
            "batch_id": batch.id,
            "status": batch.processing_status,
            "task_count": len(requests),
            "cost_savings": "50% vs standard API",
        }

    except ImportError:
        raise HTTPException(status_code=503, detail="anthropic SDK not installed")
    except Exception as e:
        logger.error("Batch API failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
