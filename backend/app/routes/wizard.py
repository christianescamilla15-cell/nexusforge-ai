"""AI Workflow Wizard — generates DAG from natural language description."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..auth.jwt_handler import verify_token
from ..llm.router import get_router

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wizard", tags=["AI Wizard"])

AGENT_CATALOG = {
    "classifier": "Classifies text into categories",
    "extractor": "Extracts structured data from text",
    "summarizer": "Generates concise summaries",
    "analyzer": "Sentiment, trends, anomaly detection",
    "enricher": "Cross-references external sources",
    "validator": "Validates output quality",
    "reporter": "Generates formatted reports",
    "repair": "Diagnoses and fixes failures",
    "normalizer": "Cleans and normalizes data",
    "researcher": "Topic research with citations",
    "translator": "Multi-language translation",
    "compliance": "Regulatory rule checking",
    "monitor": "Health metrics checking",
    "planner": "Task decomposition and planning",
    "knowledge": "Q&A with RAG retrieval",
    "scraper": "Web scraping",
    "ocr": "Image text extraction",
    "sentiment": "Emotion analysis",
    "scheduler": "Task scheduling",
    "webhook": "HTTP callback invocation",
}

SYSTEM_PROMPT = """You are the NexusForge AI Workflow Wizard. Your job is to design an optimal workflow DAG from a user's description.

Available agents:
{agents}

Available integrations (inputs):
- Google Drive (read files)
- Gmail (read emails)
- Custom Webhook (receive data)

Available integrations (outputs):
- Email (send results via Resend)
- Notion (save to database)
- Slack (send notifications)
- WhatsApp (send messages)
- Custom Webhook (POST results)
- Google Calendar (create events)

Rules:
1. Return ONLY valid JSON — no markdown, no explanation
2. Choose 3-7 agents maximum for simplicity
3. Create logical dependencies (DAG, no cycles)
4. Include at least one output integration
5. Each step must have a unique name (lowercase, underscores)

Also analyze if this task would benefit from a swarm topology instead of a linear DAG:
- "parallel" — multiple independent analyses running simultaneously (e.g. process many documents fast)
- "debate" — iterative critique/improvement loop (e.g. analyze from multiple perspectives)
- "consensus" — multiple agents vote on a decision (e.g. reach agreement between AI opinions)
- "hierarchical" — supervisor decomposes and coordinates sub-tasks (e.g. complex multi-step orchestration)
- "sequential" — ordered pipeline where each agent depends on the previous
- "adaptive" — router selects the best topology at runtime based on input complexity
If a swarm topology would be better than a DAG, set recommended_topology to one of the above values and explain why.
If a DAG is better, set recommended_topology to null.

Return this exact JSON format:
{{
  "name": "workflow name",
  "description": "what this workflow does",
  "steps": [
    {{"name": "step_name", "agent_type": "classifier", "depends_on": []}},
    {{"name": "step_name", "agent_type": "summarizer", "depends_on": ["step_name"]}}
  ],
  "suggested_integrations": {{
    "inputs": ["drive"],
    "outputs": ["email", "notion"]
  }},
  "estimated_tokens": 500,
  "estimated_cost_usd": 0.003,
  "recommended_topology": null,
  "topology_reason": null
}}"""


class WizardRequest(BaseModel):
    description: str
    industry: Optional[str] = None
    complexity: str = "medium"  # simple, medium, complex
    language: str = "en"


class WizardQuestionRequest(BaseModel):
    description: str
    language: str = "en"


@router.post("/generate")
async def generate_workflow(req: WizardRequest, request: Request):
    """Generate a workflow DAG from natural language description."""
    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or not verify_token(auth[7:]):
        raise HTTPException(status_code=401, detail="Login required")
    agents_text = "\n".join(f"- {k}: {v}" for k, v in AGENT_CATALOG.items())
    prompt = SYSTEM_PROMPT.format(agents=agents_text)

    context = f"Industry: {req.industry}. " if req.industry else ""
    context += f"Complexity: {req.complexity}. "
    user_msg = f"{context}Create a workflow for: {req.description}"

    try:
        llm = get_router()
        response = await llm.chat(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=1024,
        )

        # Parse JSON from response
        text = response.text.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        workflow = json.loads(text)

        return {
            "workflow": workflow,
            "tokens_used": response.tokens_input + response.tokens_output,
            "cost_usd": response.cost_usd,
            "provider": response.provider,
        }

    except json.JSONDecodeError:
        # LLM didn't return valid JSON — return a template
        return {
            "workflow": _fallback_workflow(req.description),
            "tokens_used": 0,
            "cost_usd": 0,
            "provider": "fallback",
            "warning": "AI generated invalid JSON — using template workflow",
        }
    except Exception as e:
        logger.warning("Wizard generation failed: %s", e)
        return {
            "workflow": _fallback_workflow(req.description),
            "tokens_used": 0,
            "cost_usd": 0,
            "provider": "fallback",
            "warning": str(e),
        }


@router.post("/questions")
async def get_wizard_questions(req: WizardQuestionRequest, request: Request):
    """Get clarifying questions before generating workflow."""
    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)
    questions = {
        "en": [
            {"id": "goal", "question": "What is the main goal of this workflow?", "type": "text"},
            {"id": "input", "question": "Where does the data come from?", "type": "select",
             "options": ["File upload", "Google Drive", "Gmail", "Webhook", "Manual text"]},
            {"id": "output", "question": "Where should results be sent?", "type": "multiselect",
             "options": ["Email", "Notion", "Slack", "WhatsApp", "Webhook", "Dashboard only"]},
            {"id": "industry", "question": "What industry is this for?", "type": "select",
             "options": ["Technology", "Finance", "Healthcare", "Legal", "Marketing", "Education", "Other"]},
            {"id": "complexity", "question": "How complex should the workflow be?", "type": "select",
             "options": ["Simple (3 agents)", "Medium (5 agents)", "Complex (7 agents)"]},
        ],
        "es": [
            {"id": "goal", "question": "Cual es el objetivo principal de este flujo?", "type": "text"},
            {"id": "input", "question": "De donde vienen los datos?", "type": "select",
             "options": ["Subir archivo", "Google Drive", "Gmail", "Webhook", "Texto manual"]},
            {"id": "output", "question": "A donde enviar los resultados?", "type": "multiselect",
             "options": ["Email", "Notion", "Slack", "WhatsApp", "Webhook", "Solo dashboard"]},
            {"id": "industry", "question": "Para que industria es?", "type": "select",
             "options": ["Tecnologia", "Finanzas", "Salud", "Legal", "Marketing", "Educacion", "Otro"]},
            {"id": "complexity", "question": "Que tan complejo debe ser?", "type": "select",
             "options": ["Simple (3 agentes)", "Medio (5 agentes)", "Complejo (7 agentes)"]},
        ],
    }
    return {"questions": questions.get(req.language, questions["en"])}


def _fallback_workflow(description: str) -> dict:
    """Template workflow when AI generation fails."""
    return {
        "name": "AI Generated Workflow",
        "description": description[:200],
        "steps": [
            {"name": "ingest", "agent_type": "extractor", "depends_on": []},
            {"name": "classify", "agent_type": "classifier", "depends_on": ["ingest"]},
            {"name": "analyze", "agent_type": "analyzer", "depends_on": ["classify"]},
            {"name": "summarize", "agent_type": "summarizer", "depends_on": ["analyze"]},
            {"name": "report", "agent_type": "reporter", "depends_on": ["summarize"]},
        ],
        "suggested_integrations": {"inputs": ["upload"], "outputs": ["email"]},
        "estimated_tokens": 400,
        "estimated_cost_usd": 0.002,
    }
