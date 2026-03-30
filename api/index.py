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

@app.get("/api/integrations/google/test")
async def google_test():
    """Test Google credentials, token, and direct Calendar API call."""
    import os
    import httpx
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    has_json = bool(creds_json.strip()) if creds_json else False
    has_path = bool(creds_path.strip()) if creds_path else False
    cal_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary").strip()

    result = {
        "GOOGLE_CREDENTIALS_JSON_set": has_json,
        "GOOGLE_CREDENTIALS_JSON_length": len(creds_json) if creds_json else 0,
        "GOOGLE_CREDENTIALS_PATH_set": has_path,
        "GOOGLE_CALENDAR_ID": cal_id,
    }

    try:
        from app.integrations.google_drive.client import _get_access_token
        token = await _get_access_token()
        result["token_result"] = token[:20] + "..." if token and not token.startswith("__") else token
        result["token_success"] = bool(token and not token.startswith("__"))

        # Direct Calendar API test
        if token and not token.startswith("__"):
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try calendarList first to see what calendars are accessible
                resp = await client.get(
                    "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                    headers={"Authorization": f"Bearer {token}"},
                )
                result["calendarList_status"] = resp.status_code
                if resp.status_code == 200:
                    cals = resp.json().get("items", [])
                    result["calendars_found"] = len(cals)
                    result["calendars"] = [{"id": c.get("id"), "summary": c.get("summary")} for c in cals[:5]]
                else:
                    result["calendarList_error"] = resp.text[:200]
    except Exception as e:
        result["error"] = str(e)

    return result

@app.get("/api/integrations/drive/files")
async def drive_files(query: str = "", limit: int = 10):
    try:
        from app.integrations.google_drive.client import list_files
        return await list_files(query=query, max_results=limit)
    except Exception as e:
        return {"status": "error", "files": [], "message": str(e)}

@app.get("/api/integrations/drive/files/{file_id}/content")
async def drive_file_content(file_id: str):
    try:
        from app.integrations.google_drive.client import get_file_content
        return await get_file_content(file_id)
    except Exception as e:
        return {"status": "error", "content": "", "message": str(e)}

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

# ── Drive-to-Intelligence Pipeline ──
@app.get("/api/workflows/drive-to-intelligence/files")
async def pipeline_files():
    try:
        from app.integrations.google_drive.client import list_files
        result = await list_files(max_results=20)
        files = [f for f in result.get("files", []) if f.get("mimeType") != "application/vnd.google-apps.folder"]
        return {"status": "success", "files": files, "total": len(files)}
    except Exception as e:
        return {"status": "error", "files": [], "message": str(e)}

@app.post("/api/workflows/drive-to-intelligence/by-name")
async def pipeline_by_name(file_name: str, language: str = "es", save_to_notion: bool = True, send_webhook: bool = True, send_email: bool = False, email_to: str = "christianescamilla15@gmail.com", send_whatsapp: bool = False, whatsapp_number: str = "525579605324"):
    """Process a Drive file by name instead of ID."""
    try:
        from app.integrations.google_drive.client import list_files
        result = await list_files(query=file_name, max_results=5)
        files = [f for f in result.get("files", []) if f.get("mimeType") != "application/vnd.google-apps.folder"]
        if not files:
            return {"status": "error", "message": f"No file found matching '{file_name}'", "available_files": []}
        # Use the first match
        file_id = files[0]["id"]
        return await pipeline_run(file_id=file_id, language=language, save_to_notion=save_to_notion, send_webhook=send_webhook, send_email=send_email, email_to=email_to, send_whatsapp=send_whatsapp, whatsapp_number=whatsapp_number)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/workflows/drive-to-intelligence/all")
async def pipeline_all(language: str = "es", save_to_notion: bool = True, send_webhook: bool = True, send_email: bool = False, email_to: str = "christianescamilla15@gmail.com", send_whatsapp: bool = False, whatsapp_number: str = "525579605324"):
    """Process ALL files in Drive folder automatically."""
    try:
        from app.integrations.google_drive.client import list_files
        result = await list_files(max_results=20)
        files = [f for f in result.get("files", []) if f.get("mimeType") != "application/vnd.google-apps.folder"]
        if not files:
            return {"status": "no_files", "results": []}
        results = []
        for f in files:
            r = await pipeline_run(file_id=f["id"], language=language, save_to_notion=save_to_notion, send_webhook=send_webhook, send_email=send_email, email_to=email_to, send_whatsapp=send_whatsapp, whatsapp_number=whatsapp_number)
            results.append({"file": f["name"], "result": r})
        return {"status": "completed", "files_processed": len(results), "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/workflows/drive-to-intelligence")
async def pipeline_run(file_id: str, language: str = "es", save_to_notion: bool = True, send_webhook: bool = True, send_email: bool = False, email_to: str = "christianescamilla15@gmail.com", send_whatsapp: bool = False, whatsapp_number: str = "525579605324"):
    import time
    from datetime import datetime
    start = time.time()
    steps = []
    try:
        from app.integrations.google_drive.client import get_file_content, list_files
        files_result = await list_files(max_results=50)
        file_meta = next((f for f in files_result.get("files", []) if f["id"] == file_id), None)
        cr = await get_file_content(file_id)
        if cr["status"] != "success":
            return {"status": "error", "pipeline_steps": ["drive_read: failed"]}
        content, file_name = cr["content"], (file_meta["name"] if file_meta else file_id)
        steps.append(f"drive_read: success ({len(content)} chars)")
    except Exception as e:
        return {"status": "error", "pipeline_steps": [f"drive_read: {e}"]}
    try:
        from app.use_cases.document_intelligence.workflow import run_document_intelligence_workflow
        from app.use_cases.document_intelligence.schemas import DocumentIntelligenceInput
        doc = (await run_document_intelligence_workflow(DocumentIntelligenceInput(content=content, filename=file_name, language=language))).model_dump()
        steps.append(f"intelligence: {doc['status']} ({doc['document_type']})")
    except Exception as e:
        return {"status": "error", "pipeline_steps": steps + [f"intelligence: {e}"]}
    notion_url = None
    if save_to_notion:
        try:
            from app.integrations.notion.client import write_page
            nr = await write_page(f"[{doc['document_type'].upper()}] {file_name}", f"Tipo: {doc['document_type']}\nResumen: {doc.get('summary','')}\nCampos: {doc.get('extracted_fields',{})}")
            notion_url = nr.get("url") if nr["status"] == "success" else None
            steps.append(f"notion: {'ok' if notion_url else 'failed'}")
        except Exception as e:
            steps.append(f"notion: {e}")
    ws = False
    if send_webhook:
        try:
            from app.integrations.webhooks.client import send_webhook
            wr = await send_webhook("document_processed", {"file": file_name, "type": doc["document_type"], "summary": doc.get("summary","")})
            ws = wr["status"] == "success"
            steps.append(f"webhook: {'ok' if ws else 'failed'}")
        except Exception as e:
            steps.append(f"webhook: {e}")
    # Email via Resend
    es = False
    if send_email:
        try:
            from app.integrations.email.client import send_email as _send_email
            subject = f"NexusForge: [{doc['document_type'].upper()}] {file_name}"
            body = f"<h2>Documento Procesado</h2><p><b>Archivo:</b> {file_name}</p><p><b>Tipo:</b> {doc['document_type']}</p><p><b>Resumen:</b> {doc.get('summary','')}</p>"
            if notion_url:
                body += f"<p><a href='{notion_url}'>Ver en Notion</a></p>"
            er = await _send_email(to=email_to, subject=subject, body=body)
            es = er["status"] == "success"
            steps.append(f"email: {'sent to ' + email_to if es else 'failed'}")
        except Exception as e:
            steps.append(f"email: {e}")
    # WhatsApp
    wl = None
    if send_whatsapp:
        try:
            from app.integrations.whatsapp.client import send_whatsapp as _send_wa
            msg = f"📄 NexusForge\n📁 {file_name}\n📋 {doc['document_type']}\n📝 {doc.get('summary','')[:200]}"
            if notion_url:
                msg += f"\n🔗 {notion_url}"
            wr2 = await _send_wa(whatsapp_number, msg)
            wl = wr2.get("whatsapp_link")
            steps.append(f"whatsapp: {wr2.get('method','link')}")
        except Exception as e:
            steps.append(f"whatsapp: {e}")
    return {"status": doc["status"], "file_name": file_name, "document_type": doc["document_type"], "extracted_fields": doc.get("extracted_fields",{}), "summary": doc.get("summary",""), "requires_human_review": doc.get("requires_human_review",False), "notion_url": notion_url, "webhook_sent": ws, "email_sent": es, "whatsapp_link": wl, "llm_used": doc.get("llm_used",False), "total_tokens": doc.get("total_tokens",0), "cost_usd": doc.get("cost_usd",0), "processing_time_ms": round((time.time()-start)*1000,1), "agents_used": doc.get("agents_used",[]), "pipeline_steps": steps, "source": "backend", "server_time": datetime.utcnow().isoformat()}

# ── Drive-to-Enterprise Ops Pipeline ──
@app.post("/api/workflows/drive-to-ops")
async def pipeline_drive_to_ops(file_id: str = "", file_name: str = "", customer_id: str = "CUST-001", language: str = "es", save_to_notion: bool = True, send_email: bool = False, email_to: str = "christianescamilla15@gmail.com", send_whatsapp: bool = False, whatsapp_number: str = "525579605324"):
    """Read a customer request/email from Drive → process with Enterprise Ops (8 agents)."""
    import time
    from datetime import datetime
    start = time.time()
    steps = []
    # Resolve file
    try:
        from app.integrations.google_drive.client import get_file_content, list_files
        if not file_id and file_name:
            result = await list_files(query=file_name, max_results=5)
            files = [f for f in result.get("files", []) if f.get("mimeType") != "application/vnd.google-apps.folder"]
            if not files:
                return {"status": "error", "message": f"No file found: '{file_name}'"}
            file_id = files[0]["id"]
            fname = files[0]["name"]
        else:
            fname = file_id
        cr = await get_file_content(file_id)
        if cr["status"] != "success":
            return {"status": "error", "pipeline_steps": ["drive_read: failed"]}
        content = cr["content"]
        steps.append(f"drive_read: success ({len(content)} chars from {fname})")
    except Exception as e:
        return {"status": "error", "pipeline_steps": [f"drive_read: {e}"]}
    # Enterprise Ops
    try:
        from app.use_cases.enterprise_ops.workflow import run_enterprise_ops_workflow
        from app.use_cases.enterprise_ops.schemas import OperationsRequest
        ops = (await run_enterprise_ops_workflow(OperationsRequest(message=content[:2000], customer_id=customer_id, language=language))).model_dump()
        steps.append(f"enterprise_ops: {ops['status']} (intent: {ops.get('intent','?')}, agents: {len(ops.get('agents_used',[]))})")
    except Exception as e:
        return {"status": "error", "pipeline_steps": steps + [f"enterprise_ops: {e}"]}
    # Notion
    notion_url = None
    if save_to_notion:
        try:
            from app.integrations.notion.client import write_page
            title = f"[OPS] {ops.get('intent','request')} - {fname}"
            body = f"Intent: {ops.get('intent','')}\nCliente: {ops.get('customer_name','')}\nRespuesta: {ops.get('response_message','')}\nAcciones: {', '.join(ops.get('actions_taken',[]))}"
            nr = await write_page(title=title, content=body)
            notion_url = nr.get("url") if nr["status"] == "success" else None
            steps.append(f"notion: {'ok' if notion_url else 'failed'}")
        except Exception as e:
            steps.append(f"notion: {e}")
    # Email
    es = False
    if send_email:
        try:
            from app.integrations.email.client import send_email as _se
            er = await _se(to=email_to, subject=f"NexusForge Ops: {ops.get('intent','')}", body=f"<h2>Solicitud Procesada</h2><p><b>Intent:</b> {ops.get('intent','')}</p><p><b>Cliente:</b> {ops.get('customer_name','')}</p><p><b>Respuesta:</b> {ops.get('response_message','')}</p>")
            es = er["status"] == "success"
            steps.append(f"email: {'sent' if es else 'failed'}")
        except Exception as e:
            steps.append(f"email: {e}")
    # WhatsApp
    wl = None
    if send_whatsapp:
        try:
            from app.integrations.whatsapp.client import send_whatsapp as _sw
            msg = f"🏢 NexusForge Ops\n📋 {ops.get('intent','')}\n👤 {ops.get('customer_name','')}\n💬 {ops.get('response_message','')[:200]}"
            wr = await _sw(whatsapp_number, msg)
            wl = wr.get("whatsapp_link")
            steps.append(f"whatsapp: {wr.get('method','link')}")
        except Exception as e:
            steps.append(f"whatsapp: {e}")
    return {"status": ops["status"], "file_name": fname, "intent": ops.get("intent"), "customer_name": ops.get("customer_name"), "response_message": ops.get("response_message",""), "actions_taken": ops.get("actions_taken",[]), "notion_url": notion_url, "email_sent": es, "whatsapp_link": wl, "llm_used": ops.get("llm_used",False), "total_tokens": ops.get("total_tokens",0), "cost_usd": ops.get("cost_usd",0), "agents_used": ops.get("agents_used",[]), "pipeline_steps": steps, "processing_time_ms": round((time.time()-start)*1000,1), "source": "backend", "server_time": datetime.utcnow().isoformat()}

# ── Drive-to-Portfolio Copilot Pipeline ──
@app.post("/api/workflows/drive-to-copilot")
async def pipeline_drive_to_copilot(file_id: str = "", file_name: str = "", language: str = "es", save_to_notion: bool = True, send_email: bool = False, email_to: str = "christianescamilla15@gmail.com", send_whatsapp: bool = False, whatsapp_number: str = "525579605324"):
    """Read questions from Drive → answer with Portfolio Copilot (6 agents)."""
    import time
    from datetime import datetime
    start = time.time()
    steps = []
    # Resolve file
    try:
        from app.integrations.google_drive.client import get_file_content, list_files
        if not file_id and file_name:
            result = await list_files(query=file_name, max_results=5)
            files = [f for f in result.get("files", []) if f.get("mimeType") != "application/vnd.google-apps.folder"]
            if not files:
                return {"status": "error", "message": f"No file found: '{file_name}'"}
            file_id = files[0]["id"]
            fname = files[0]["name"]
        else:
            fname = file_id
        cr = await get_file_content(file_id)
        if cr["status"] != "success":
            return {"status": "error", "pipeline_steps": ["drive_read: failed"]}
        content = cr["content"]
        steps.append(f"drive_read: success ({len(content)} chars from {fname})")
    except Exception as e:
        return {"status": "error", "pipeline_steps": [f"drive_read: {e}"]}
    # Process each line as a question (or full content as one question)
    lines = [l.strip() for l in content.split("\n") if l.strip() and len(l.strip()) > 10]
    questions = lines[:5] if len(lines) > 1 else [content[:1000]]
    all_answers = []
    try:
        from app.use_cases.portfolio_copilot.workflow import run_portfolio_copilot_workflow
        from app.use_cases.portfolio_copilot.schemas import PortfolioCopilotInput
        for q in questions:
            r = (await run_portfolio_copilot_workflow(PortfolioCopilotInput(question=q, language=language))).model_dump()
            all_answers.append({"question": q[:100], "answer": r.get("final_answer",""), "recommended": r.get("recommended_project"), "skills": r.get("related_skills",[])[:5], "tokens": r.get("total_tokens",0)})
        steps.append(f"copilot: {len(all_answers)} questions answered")
    except Exception as e:
        return {"status": "error", "pipeline_steps": steps + [f"copilot: {e}"]}
    total_tokens = sum(a.get("tokens",0) for a in all_answers)
    # Notion
    notion_url = None
    if save_to_notion:
        try:
            from app.integrations.notion.client import write_page
            body = "\n\n".join([f"Q: {a['question']}\nA: {a['answer']}" for a in all_answers])
            nr = await write_page(title=f"[COPILOT] {fname} ({len(all_answers)} preguntas)", content=body)
            notion_url = nr.get("url") if nr["status"] == "success" else None
            steps.append(f"notion: {'ok' if notion_url else 'failed'}")
        except Exception as e:
            steps.append(f"notion: {e}")
    # Email
    es = False
    if send_email:
        try:
            from app.integrations.email.client import send_email as _se
            html = "<h2>Portfolio Copilot - Respuestas</h2>"
            for a in all_answers:
                html += f"<h3>{a['question']}</h3><p>{a['answer']}</p><hr>"
            er = await _se(to=email_to, subject=f"NexusForge Copilot: {len(all_answers)} respuestas", body=html)
            es = er["status"] == "success"
            steps.append(f"email: {'sent' if es else 'failed'}")
        except Exception as e:
            steps.append(f"email: {e}")
    # WhatsApp
    wl = None
    if send_whatsapp:
        try:
            from app.integrations.whatsapp.client import send_whatsapp as _sw
            msg = f"🧠 NexusForge Copilot\n📁 {fname}\n📊 {len(all_answers)} preguntas respondidas\n\n"
            for a in all_answers[:3]:
                msg += f"❓ {a['question'][:50]}...\n💡 {a['answer'][:100]}...\n\n"
            wr = await _sw(whatsapp_number, msg)
            wl = wr.get("whatsapp_link")
            steps.append(f"whatsapp: {wr.get('method','link')}")
        except Exception as e:
            steps.append(f"whatsapp: {e}")
    return {"status": "completed", "file_name": fname, "questions_answered": len(all_answers), "answers": all_answers, "total_tokens": total_tokens, "notion_url": notion_url, "email_sent": es, "whatsapp_link": wl, "pipeline_steps": steps, "processing_time_ms": round((time.time()-start)*1000,1), "source": "backend", "server_time": datetime.utcnow().isoformat()}

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
