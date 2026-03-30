"""
Drive-to-Intelligence Pipeline + WhatsApp/Email notifications
Reads file from Drive -> Document Intelligence -> Notion -> Webhook -> WhatsApp/Email
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
import time

router = APIRouter(prefix="/workflows", tags=["Automated Workflows"])


class DrivePipelineInput(BaseModel):
    file_id: str
    language: str = "es"
    save_to_notion: bool = True
    send_webhook: bool = True
    send_whatsapp: bool = False
    send_email: bool = False
    whatsapp_number: str = ""
    email_to: str = ""


@router.post("/drive-to-intelligence")
async def drive_to_intelligence(request: DrivePipelineInput):
    """Full pipeline: Drive -> Intelligence -> Notion -> Webhook -> WhatsApp/Email."""
    start = time.time()
    steps = []

    # Step 1: Read from Drive
    try:
        from ..integrations.google_drive.client import get_file_content, list_files
        files_result = await list_files(max_results=50)
        file_meta = next((f for f in files_result.get("files", []) if f["id"] == request.file_id), None)
        content_result = await get_file_content(request.file_id)
        if content_result["status"] != "success":
            return {"status": "error", "pipeline_steps": [f"drive_read: failed - {content_result.get('message', '')}"]}
        content = content_result["content"]
        file_name = file_meta["name"] if file_meta else request.file_id
        steps.append(f"drive_read: success ({len(content)} chars from {file_name})")
    except Exception as e:
        return {"status": "error", "pipeline_steps": [f"drive_read: {e}"]}

    # Step 2: Document Intelligence
    try:
        from ..use_cases.document_intelligence.workflow import run_document_intelligence_workflow
        from ..use_cases.document_intelligence.schemas import DocumentIntelligenceInput
        doc_result = await run_document_intelligence_workflow(
            DocumentIntelligenceInput(content=content, filename=file_name, language=request.language)
        )
        doc = doc_result.model_dump()
        steps.append(f"intelligence: {doc['status']} (type: {doc['document_type']}, {len(doc.get('agents_used', []))} agents)")
    except Exception as e:
        return {"status": "error", "pipeline_steps": steps + [f"intelligence: {e}"]}

    # Step 3: Notion
    notion_url = None
    if request.save_to_notion:
        try:
            from ..integrations.notion.client import write_page
            title = f"[{doc['document_type'].upper()}] {file_name}"
            body = f"Tipo: {doc['document_type']}\n"
            body += f"Resumen: {doc.get('summary', 'N/A')}\n\n"
            body += f"Campos extraidos:\n"
            for k, v in doc.get("extracted_fields", {}).items():
                body += f"  - {k}: {v}\n"
            if doc.get("requires_human_review"):
                body += f"\nRequiere revision humana"
            body += f"\n\nTokens: {doc.get('total_tokens', 0)} | Costo: ${doc.get('cost_usd', 0)}"
            nr = await write_page(title=title, content=body)
            notion_url = nr.get("url") if nr["status"] == "success" else None
            steps.append(f"notion: {'success' if notion_url else 'failed'}")
        except Exception as e:
            steps.append(f"notion: error - {e}")

    # Step 4: Webhook
    webhook_sent = False
    if request.send_webhook:
        try:
            from ..integrations.webhooks.client import send_webhook
            wr = await send_webhook("document_processed", {
                "file": file_name, "type": doc["document_type"],
                "summary": doc.get("summary", ""), "notion_url": notion_url,
            })
            webhook_sent = wr["status"] == "success"
            steps.append(f"webhook: {'success' if webhook_sent else 'failed'}")
        except Exception as e:
            steps.append(f"webhook: error - {e}")

    # Step 5: WhatsApp
    whatsapp_sent = False
    wa_link = None
    if request.send_whatsapp:
        try:
            from ..integrations.whatsapp.client import send_whatsapp
            phone = request.whatsapp_number or "525579605324"
            msg = f"*NexusForge - Documento Procesado*\n\n"
            msg += f"Archivo: {file_name}\n"
            msg += f"Tipo: {doc['document_type']}\n"
            msg += f"Resumen: {doc.get('summary', 'N/A')[:200]}\n"
            if doc.get("requires_human_review"):
                msg += f"\nRequiere revision humana"
            if notion_url:
                msg += f"\nNotion: {notion_url}"
            wa_result = await send_whatsapp(phone, msg)
            whatsapp_sent = wa_result["status"] == "success"
            wa_link = wa_result.get("whatsapp_link")
            steps.append(f"whatsapp: {wa_result['method']} ({'success' if whatsapp_sent else 'failed'})")
        except Exception as e:
            steps.append(f"whatsapp: error - {e}")

    # Step 6: Email via Resend
    email_sent = False
    if request.send_email:
        try:
            from ..integrations.email.client import send_email
            email_to = request.email_to or "christianescamilla15@gmail.com"
            subject = f"NexusForge: [{doc['document_type'].upper()}] {file_name}"
            html_body = f"<h2>Documento Procesado por NexusForge</h2>"
            html_body += f"<p><strong>Archivo:</strong> {file_name}</p>"
            html_body += f"<p><strong>Tipo:</strong> {doc['document_type']}</p>"
            html_body += f"<p><strong>Resumen:</strong> {doc.get('summary', 'N/A')}</p>"
            if doc.get("extracted_fields"):
                html_body += f"<h3>Campos extraidos:</h3><ul>"
                for k, v in doc["extracted_fields"].items():
                    html_body += f"<li><strong>{k}:</strong> {v}</li>"
                html_body += "</ul>"
            if doc.get("requires_human_review"):
                html_body += f"<p><strong>Requiere revision humana</strong></p>"
            if notion_url:
                html_body += f"<p><a href='{notion_url}'>Ver en Notion</a></p>"
            html_body += f"<hr><p><small>Tokens: {doc.get('total_tokens', 0)} | Costo: ${doc.get('cost_usd', 0)} | Agentes: {len(doc.get('agents_used', []))}</small></p>"
            email_result = await send_email(to=email_to, subject=subject, html_body=html_body)
            email_sent = email_result["status"] == "success"
            steps.append(f"email: {'sent to ' + email_to if email_sent else 'failed - ' + email_result.get('message', '')}")
        except Exception as e:
            steps.append(f"email: error - {e}")

    processing_time = round((time.time() - start) * 1000, 1)

    # Persist run to DB (best-effort)
    run_id = None
    try:
        from ..db.client import get_db_pool
        from ..db.pipeline_store import save_pipeline_run
        pool = await get_db_pool()
        run_id = await save_pipeline_run(
            pool,
            pipeline_name="drive-to-intelligence",
            status=doc["status"],
            trigger_source="backend",
            file_name=file_name,
            document_type=doc.get("document_type"),
            input_summary={"file_id": request.file_id, "language": request.language},
            output_summary={"summary": doc.get("summary", ""), "extracted_fields": doc.get("extracted_fields", {})},
            steps=steps,
            total_tokens=doc.get("total_tokens", 0),
            cost_usd=doc.get("cost_usd", 0),
            processing_time_ms=int(processing_time),
            llm_used=doc.get("llm_used", False),
            agents_used=doc.get("agents_used", []),
            notion_url=notion_url,
            webhook_sent=webhook_sent,
        )
    except Exception:
        pass

    from datetime import datetime
    return {
        "status": doc["status"],
        "run_id": run_id,
        "file_name": file_name,
        "file_content_length": len(content),
        "document_type": doc["document_type"],
        "extracted_fields": doc.get("extracted_fields", {}),
        "summary": doc.get("summary", ""),
        "validation_errors": doc.get("validation_errors", []),
        "requires_human_review": doc.get("requires_human_review", False),
        "notion_url": notion_url,
        "webhook_sent": webhook_sent,
        "whatsapp_link": wa_link if request.send_whatsapp else None,
        "whatsapp_sent": whatsapp_sent,
        "email_sent": email_sent,
        "llm_used": doc.get("llm_used", False),
        "total_tokens": doc.get("total_tokens", 0),
        "cost_usd": doc.get("cost_usd", 0),
        "processing_time_ms": processing_time,
        "agents_used": doc.get("agents_used", []),
        "pipeline_steps": steps,
        "source": "backend",
        "server_time": datetime.utcnow().isoformat(),
    }


@router.get("/drive-to-intelligence/files")
async def list_drive_files():
    """List available files from Google Drive."""
    try:
        from ..integrations.google_drive.client import list_files
        result = await list_files(max_results=20)
        files = [f for f in result.get("files", []) if f.get("mimeType") != "application/vnd.google-apps.folder"]
        return {"status": "success", "files": files, "total": len(files)}
    except Exception as e:
        return {"status": "error", "files": [], "message": str(e)}


@router.post("/drive-to-intelligence/by-name")
async def drive_to_intelligence_by_name(
    file_name: str = Query(..., description="File name or partial name to search"),
    language: str = Query("es"),
    save_to_notion: bool = Query(True),
    send_email: bool = Query(False),
):
    """Find a Drive file by name and process it."""
    try:
        from ..integrations.google_drive.client import list_files
        result = await list_files(max_results=50)
        files = [f for f in result.get("files", []) if f.get("mimeType") != "application/vnd.google-apps.folder"]

        # Search by partial name (case insensitive)
        match = None
        name_lower = file_name.lower()
        for f in files:
            if name_lower in f["name"].lower():
                match = f
                break

        if not match:
            return {"status": "error", "message": f"No file matching '{file_name}' found in Drive"}

        # Reuse the main pipeline with a mock request
        from pydantic import BaseModel
        class Req(BaseModel):
            file_id: str
            language: str = "es"
            save_to_notion: bool = True
            send_webhook: bool = False
            send_whatsapp: bool = False
            send_email: bool = False
            whatsapp_number: str = ""
            email_to: str = ""

        req = Req(file_id=match["id"], language=language, save_to_notion=save_to_notion, send_email=send_email)
        return await drive_to_intelligence(req)
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/drive-to-intelligence/runs")
async def get_pipeline_runs(
    pipeline: Optional[str] = Query(None, description="Filter by pipeline name"),
    limit: int = Query(20, ge=1, le=100),
):
    """List persisted pipeline run history."""
    try:
        from ..db.client import get_db_pool
        from ..db.pipeline_store import list_pipeline_runs
        pool = await get_db_pool()
        runs = await list_pipeline_runs(pool, pipeline_name=pipeline, limit=limit)
        for run in runs:
            run["id"] = str(run["id"])
            if run.get("created_at"):
                run["created_at"] = run["created_at"].isoformat()
        return {"status": "success", "runs": runs, "total": len(runs)}
    except Exception as e:
        return {"status": "error", "runs": [], "message": str(e)}
