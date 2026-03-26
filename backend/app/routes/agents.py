"""Agent listing routes."""

import logging
from fastapi import APIRouter, HTTPException

from app.agents.registry import list_agents, get_agent

router = APIRouter()
logger = logging.getLogger(__name__)


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
