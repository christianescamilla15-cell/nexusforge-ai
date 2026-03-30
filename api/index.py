"""
NexusForge AI — Serverless API for Vercel
Lightweight version that runs the 3 real use cases without PostgreSQL/Redis.
Uses in-memory tracking and local fixtures.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

app = FastAPI(title="NexusForge AI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ──
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "mode": "serverless"}

# ── Enterprise Operations ──
class OpsRequest(BaseModel):
    message: str
    customer_id: Optional[str] = None
    language: str = "es"
    priority: str = "normal"

@app.post("/api/enterprise-ops/process")
async def enterprise_ops(request: OpsRequest):
    from datetime import datetime
    try:
        from app.use_cases.enterprise_ops.workflow import run_enterprise_ops_workflow
        from app.use_cases.enterprise_ops.schemas import OperationsRequest
        req = OperationsRequest(**request.model_dump())
        result = await run_enterprise_ops_workflow(req)
        data = result.model_dump()
        data["source"] = "backend"
        data["server_time"] = datetime.utcnow().isoformat()
        return data
    except Exception as e:
        return {"status": "error", "error": str(e), "run_id": "serverless", "source": "backend"}

@app.get("/api/enterprise-ops/health")
async def enterprise_ops_health():
    return {
        "status": "operational",
        "agents": ["IntakeAgent", "IntentClassifierAgent", "CustomerContextAgent", "DocumentRAGAgent", "SchedulerAgent", "CRMUpdateAgent", "NotificationAgent", "SupervisorAgent"],
        "mode": "serverless",
    }

# ── Document Intelligence ──
class DocRequest(BaseModel):
    content: str
    filename: Optional[str] = None
    language: str = "es"
    document_type_hint: Optional[str] = None

@app.post("/api/document-intelligence/run")
async def document_intelligence(request: DocRequest):
    from datetime import datetime
    try:
        from app.use_cases.document_intelligence.workflow import run_document_intelligence_workflow
        from app.use_cases.document_intelligence.schemas import DocumentIntelligenceInput
        req = DocumentIntelligenceInput(**request.model_dump())
        result = await run_document_intelligence_workflow(req)
        data = result.model_dump()
        data["source"] = "backend"
        data["server_time"] = datetime.utcnow().isoformat()
        return data
    except Exception as e:
        return {"status": "error", "error": str(e), "run_id": "serverless", "source": "backend"}

@app.get("/api/document-intelligence/examples")
async def doc_examples():
    try:
        from app.use_cases.document_intelligence.services import load_sample_documents
        docs = load_sample_documents()
        return {"documents": [{"id": d["id"], "filename": d["filename"], "type": d["type"], "preview": d["content"][:100]} for d in docs]}
    except Exception as e:
        return {"documents": [], "error": str(e)}

# ── Portfolio Copilot ──
class CopilotRequest(BaseModel):
    question: str
    language: str = "es"
    context: Optional[str] = None

@app.post("/api/portfolio-copilot/run")
async def portfolio_copilot(request: CopilotRequest):
    from datetime import datetime
    try:
        from app.use_cases.portfolio_copilot.workflow import run_portfolio_copilot_workflow
        from app.use_cases.portfolio_copilot.schemas import PortfolioCopilotInput
        req = PortfolioCopilotInput(**request.model_dump())
        result = await run_portfolio_copilot_workflow(req)
        data = result.model_dump()
        data["source"] = "backend"
        data["server_time"] = datetime.utcnow().isoformat()
        return data
    except Exception as e:
        return {"status": "error", "error": str(e), "run_id": "serverless", "source": "backend"}

@app.get("/api/portfolio-copilot/examples")
async def copilot_examples():
    try:
        from app.use_cases.portfolio_copilot.services import load_interview_questions
        return {"questions": load_interview_questions()}
    except Exception as e:
        return {"questions": [], "error": str(e)}

# ── Provider Status ──
@app.get("/api/providers/status")
async def providers_status():
    import os
    groq_key = os.environ.get("GROQ_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    return {
        "groq": {"configured": bool(groq_key), "model": "llama-3.3-70b-versatile", "key_prefix": groq_key[:8] + "..." if groq_key else ""},
        "claude": {"configured": bool(anthropic_key), "model": "claude-sonnet-4-20250514"},
        "openai": {"configured": bool(openai_key), "model": "gpt-4o"},
        "active_provider": (
            "groq" if groq_key
            else "claude" if anthropic_key
            else "openai" if openai_key
            else "none"
        ),
    }

@app.get("/api/providers/test")
async def test_provider():
    """Test the active LLM provider with a simple prompt."""
    try:
        from app.use_cases.shared.llm_client import llm_generate
        result = await llm_generate("Say hello in one word.", system="Respond briefly.", max_tokens=10)
        return result
    except Exception as e:
        return {"error": str(e), "llm_used": False}

# ── Runs (in-memory) ──
@app.get("/api/runs")
async def list_runs():
    try:
        from app.metrics.collector import collector
        runs = collector.get_runs()
        return {"runs": [r.model_dump() for r in runs], "total": len(runs)}
    except Exception:
        return {"runs": [], "total": 0}

@app.get("/api/runs/reliability/health")
@app.get("/api/reliability/health")
async def reliability_health():
    try:
        from app.metrics.reliability import get_system_health
        return get_system_health()
    except Exception:
        return {"total_runs": 0, "successful_runs": 0, "system_success_rate": 0, "total_agents_tracked": 0, "agents": []}

@app.get("/api/runs/reliability/agents")
@app.get("/api/reliability/agents")
async def reliability_agents():
    try:
        from app.metrics.reliability import compute_agent_reliability
        scores = compute_agent_reliability()
        return {"agents": [vars(s) for s in scores]}
    except Exception:
        return {"agents": []}

# ── Integrations ──
@app.get("/api/integrations/status")
async def integration_status():
    from app.integrations.config import IntegrationConfig
    return IntegrationConfig.status()

@app.get("/api/integrations/drive/files")
async def drive_files(query: str = "", limit: int = 10):
    try:
        from app.integrations.google_drive.client import list_files
        return await list_files(query=query, max_results=limit)
    except Exception as e:
        return {"status": "error", "files": [], "message": str(e)}

@app.get("/api/integrations/gmail/messages")
async def gmail_messages(query: str = "is:unread", limit: int = 5):
    try:
        from app.integrations.gmail.client import list_messages
        return await list_messages(query=query, max_results=limit)
    except Exception as e:
        return {"status": "error", "messages": [], "message": str(e)}

@app.get("/api/integrations/calendar/events")
async def calendar_events(days: int = 7, limit: int = 10):
    try:
        from app.integrations.google_calendar.client import list_events
        return await list_events(days_ahead=days, max_results=limit)
    except Exception as e:
        return {"status": "error", "events": [], "message": str(e)}

@app.get("/api/integrations/calendar/availability")
async def calendar_avail(date: str = None):
    try:
        from app.integrations.google_calendar.client import get_availability
        return await get_availability(date=date)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/integrations/notion/write")
async def notion_write_api(title: str = "Test", content: str = ""):
    try:
        from app.integrations.notion.client import write_page
        return await write_page(title=title, content=content)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/integrations/notion/query")
async def notion_query_api():
    try:
        from app.integrations.notion.client import query_database
        return await query_database()
    except Exception as e:
        return {"status": "error", "results": [], "message": str(e)}

@app.post("/api/integrations/webhook/send")
async def webhook_send_api(event_type: str = "test", url: str = None):
    try:
        from app.integrations.webhooks.client import send_webhook
        return await send_webhook(event_type=event_type, payload={"test": True}, url=url)
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── Feedback Loop ──
@app.post("/api/feedback/submit")
async def submit_feedback_api(run_id: str, rating: int = 3, approved: bool = False, comments: str = "", reviewer: str = "anonymous"):
    from app.services.feedback_service import submit_feedback
    result = submit_feedback(run_id=run_id, rating=rating, approved=approved, comments=comments, reviewer=reviewer)
    return result.model_dump()

@app.get("/api/feedback/stats")
async def feedback_stats_api():
    from app.services.feedback_service import get_feedback_stats
    return get_feedback_stats()

@app.get("/api/feedback/agents/performance")
async def agent_perf_api():
    from app.services.feedback_service import get_agent_performance
    agents = get_agent_performance()
    return {"agents": [a.model_dump() for a in agents]}

@app.get("/api/feedback/agents/recommendations")
async def agent_recs_api():
    from app.services.feedback_service import get_agent_recommendations
    return get_agent_recommendations()
