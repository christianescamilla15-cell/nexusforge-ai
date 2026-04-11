"""Agent listing and per-user config routes."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.agents.registry import list_agents, get_agent
from app.agents.schemas import get_triggers, get_transforms, get_actions, AGENT_SCHEMAS
from app.auth.jwt_handler import verify_token
from app.db.client import get_db_pool

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_user_id(request: Request) -> Optional[str]:
    """Extract user_id from JWT, or None for anonymous."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        data = verify_token(auth[7:])
        if data:
            return data.get("sub")
    return None


# Static metadata for each agent type (avoids DB dependency)
AGENT_METADATA = {
    "classifier": {
        "name": "ClassifierAgent",
        "description": "Classifies documents into categories: legal, financial, technical, medical, general.",
        "tools": ["llm_chat"],
    },
    "extractor": {
        "name": "ExtractorAgent",
        "description": "Extracts structured data (entities, fields, tables) from unstructured text.",
        "tools": ["llm_chat", "regex"],
    },
    "summarizer": {
        "name": "SummarizerAgent",
        "description": "Generates concise summaries of long documents or multi-step outputs.",
        "tools": ["llm_chat"],
    },
    "analyzer": {
        "name": "AnalyzerAgent",
        "description": "Performs deep analysis: sentiment, trends, anomalies, comparisons.",
        "tools": ["llm_chat", "statistics"],
    },
    "enricher": {
        "name": "EnricherAgent",
        "description": "Enriches data by cross-referencing external sources and knowledge base.",
        "tools": ["llm_chat", "rag_search", "web_search"],
    },
    "validator": {
        "name": "ValidatorAgent",
        "description": "Quality gate: validates completeness, consistency, and accuracy of agent outputs.",
        "tools": ["llm_chat"],
    },
    "reporter": {
        "name": "ReporterAgent",
        "description": "Generates formatted reports (Markdown, JSON) from workflow results.",
        "tools": ["llm_chat", "template_engine"],
    },
    "repair": {
        "name": "RepairAgent",
        "description": "Analyzes failed workflow steps and suggests fixes for self-healing.",
        "tools": ["llm_chat", "config_editor"],
    },
    "compliance": {
        "name": "ComplianceAgent",
        "description": "Verifies documents and processes against regulatory frameworks (GDPR, SOX, HIPAA).",
        "tools": ["llm_chat", "policy_check"],
    },
    "critic": {
        "name": "CriticAgent",
        "description": "Reviews and critiques outputs from other agents, suggesting improvements and catching errors.",
        "tools": ["llm_chat", "scoring"],
    },
    "judge": {
        "name": "JudgeAgent",
        "description": "Evaluates consensus between multiple agents and selects the best output.",
        "tools": ["llm_chat", "voting"],
    },
    "knowledge": {
        "name": "KnowledgeAgent",
        "description": "Manages the knowledge base: indexes documents, performs semantic search (RAG).",
        "tools": ["llm_chat", "rag_search", "embeddings"],
    },
    "monitor": {
        "name": "MonitorAgent",
        "description": "Monitors system metrics, detects anomalies, and triggers alerts when thresholds are exceeded.",
        "tools": ["metrics_check", "alert_trigger"],
    },
    "normalizer": {
        "name": "NormalizerAgent",
        "description": "Normalizes and cleans data: standardizes formats, removes duplicates, fixes encoding.",
        "tools": ["llm_chat", "data_transform"],
    },
    "ocr": {
        "name": "OCRAgent",
        "description": "Extracts text from images and scanned PDFs using optical character recognition.",
        "tools": ["llm_chat", "image_processing"],
    },
    "planner": {
        "name": "PlannerAgent",
        "description": "Creates execution plans by decomposing complex tasks into ordered sub-tasks.",
        "tools": ["llm_chat", "task_decomposition"],
    },
    "researcher": {
        "name": "ResearcherAgent",
        "description": "Researches topics by gathering information from multiple sources and synthesizing findings.",
        "tools": ["llm_chat", "web_search", "rag_search"],
    },
    "router": {
        "name": "RouterAgent",
        "description": "Routes tasks to the most appropriate agent based on content analysis and workload.",
        "tools": ["llm_chat", "agent_selector"],
    },
    "router_agent": {
        "name": "RouterAgent (Adaptive)",
        "description": "Adaptive router that dynamically selects agents based on performance history and task complexity.",
        "tools": ["llm_chat", "agent_selector", "performance_history"],
    },
    "scheduler": {
        "name": "SchedulerAgent",
        "description": "Manages scheduling: creates, updates, and cancels calendar events and reminders.",
        "tools": ["llm_chat", "calendar_api"],
    },
    "scraper": {
        "name": "ScraperAgent",
        "description": "Collects and extracts structured data from web sources and APIs.",
        "tools": ["llm_chat", "http_client"],
    },
    "sentiment": {
        "name": "SentimentAgent",
        "description": "Analyzes emotional tone and sentiment of text: positive, negative, neutral, with confidence scores.",
        "tools": ["llm_chat", "scoring"],
    },
    "translator": {
        "name": "TranslatorAgent",
        "description": "Translates text between languages while preserving technical terminology and context.",
        "tools": ["llm_chat"],
    },
    "webhook": {
        "name": "WebhookAgent",
        "description": "Sends HTTP webhooks to external services with configurable payloads and retry logic.",
        "tools": ["http_client", "retry_logic"],
    },
}


@router.get("/blocks")
async def list_composable_blocks():
    """Return all available triggers, transforms, and actions for the visual builder."""
    return {
        "triggers": get_triggers(),
        "transforms": get_transforms(),
        "actions": get_actions(),
        "total": len(AGENT_SCHEMAS),
    }


@router.get("/skills")
async def list_agent_skills():
    """Phase 5a — list available Agent Skills loaded from
    ``backend/skills/<name>/SKILL.md``.

    Reads the frontmatter of every skill directory and returns the
    parsed ``name`` / ``description`` pairs. The skill body is NOT
    included in the response to keep payloads small; callers can
    look up individual bodies in the repo directly.

    This endpoint is unauthenticated and read-only. The skills
    directory is repo-local, not user-writable, so the listing is
    stable across requests (cached in the loader singleton).
    """
    from app.agents.skill_loader import get_default_loader
    loader = get_default_loader()
    skills = loader.list_skills()
    return {
        "count": len(skills),
        "skills": [skill.to_dict() for skill in skills],
    }


@router.get("/")
async def list_all_agents():
    """Return all registered agents with metadata."""
    registered = list_agents()
    agents = []
    for agent_type in registered:
        meta = AGENT_METADATA.get(agent_type, {})
        agents.append({
            "agent_type": agent_type,
            "name": meta.get("name", agent_type),
            "description": meta.get("description", ""),
            "tools": meta.get("tools", []),
            "status": "active",
        })
    return agents


@router.get("/{agent_type}")
async def get_agent_details(agent_type: str):
    """Return details for a specific agent type."""
    try:
        agent = get_agent(agent_type)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Agent type '{agent_type}' not found")

    meta = AGENT_METADATA.get(agent_type, {})
    return {
        "agent_type": agent_type,
        "name": getattr(agent, "name", meta.get("name", agent_type)),
        "description": getattr(agent, "description", meta.get("description", "")),
        "tools": meta.get("tools", []),
        "status": "active",
        "config_schema": getattr(agent, "config_schema", {}),
    }


# ── Per-user agent config ─────────────────────────────────────────────────────

class AgentConfigRequest(BaseModel):
    provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.3
    max_tokens: int = 1024
    system_prompt: Optional[str] = None
    tools: list[str] = []
    status: str = "active"


@router.get("/{agent_type}/config")
async def get_agent_config(agent_type: str, request: Request):
    """Return user's saved config for this agent, or defaults."""
    user_id = _get_user_id(request)
    meta = AGENT_METADATA.get(agent_type, {})
    defaults = {
        "agent_type": agent_type,
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.3,
        "max_tokens": 1024,
        "system_prompt": None,
        "tools": meta.get("tools", []),
        "status": "active",
    }

    if not user_id:
        return {**defaults, "is_custom": False}

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM agent_configs WHERE user_id = $1::uuid AND agent_type = $2",
            user_id, agent_type,
        )

    if not row:
        return {**defaults, "is_custom": False}

    return {
        "agent_type": agent_type,
        "provider": row["provider"],
        "model": row["model"],
        "temperature": float(row["temperature"]),
        "max_tokens": row["max_tokens"],
        "system_prompt": row["system_prompt"],
        "tools": row["tools"] or [],
        "status": row["status"],
        "is_custom": True,
    }


@router.put("/{agent_type}/config")
async def save_agent_config(agent_type: str, body: AgentConfigRequest, request: Request):
    """Upsert user's config for this agent."""
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Login required to save agent config")

    import json
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO agent_configs
                   (user_id, agent_type, provider, model, temperature, max_tokens,
                    system_prompt, tools, status, updated_at)
               VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, now())
               ON CONFLICT (user_id, agent_type) DO UPDATE SET
                   provider = $3, model = $4, temperature = $5, max_tokens = $6,
                   system_prompt = $7, tools = $8::jsonb, status = $9, updated_at = now()""",
            user_id, agent_type, body.provider, body.model,
            body.temperature, body.max_tokens, body.system_prompt,
            json.dumps(body.tools), body.status,
        )

    return {"saved": True, "agent_type": agent_type}
