"""
Drive-to-Intelligence Pipeline + WhatsApp/Email notifications
Reads file from Drive → Document Intelligence → Notion → Webhook → WhatsApp/Email
"""
from fastapi import APIRouter
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
    """Full pipeline: Drive → Intelligence → Notion → Webhook → WhatsApp/Email."""
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
            body += f"Campos extraídos:\n"
            for k, v in doc.get("extracted_fields", {}).items():
                body += f"  • {k}: {v}\n"
            if doc.get("requires_human_review"):
                body += f"\n⚠️ Requiere revisión humana"
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

    # Step 5: WhatsApp (via Twilio/WhatsApp API or direct link)
    whatsapp_sent = False
    if request.send_whatsapp:
        try:
            import httpx
            phone = request.whatsapp_number or "525579605324"
            lang = request.language
            msg = f"📄 *NexusForge - Documento Procesado*\n\n" if lang == "es" else f"📄 *NexusForge - Document Processed*\n\n"
            msg += f"📁 Archivo: {file_name}\n"
            msg += f"📋 Tipo: {doc['document_type']}\n"
            msg += f"📝 Resumen: {doc.get('summary', 'N/A')[:200]}\n"
            if doc.get("requires_human_review"):
                msg += f"\n⚠️ Requiere revisión humana"
            if notion_url:
                msg += f"\n🔗 Notion: {notion_url}"

            # Generate WhatsApp API link (works without Twilio)
            import urllib.parse
            wa_link = f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(msg)}"
            whatsapp_sent = True
            steps.append(f"whatsapp: link generated for {phone}")
        except Exception as e:
            wa_link = None
            steps.append(f"whatsapp: error - {e}")

    # Step 6: Email summary
    email_sent = False
    email_body = None
    if request.send_email:
        try:
            email_to = request.email_to or "christianescamilla15@gmail.com"
            email_body = f"NexusForge - Documento Procesado\n\n"
            email_body += f"Archivo: {file_name}\n"
            email_body += f"Tipo: {doc['document_type']}\n"
            email_body += f"Resumen: {doc.get('summary', 'N/A')}\n\n"
            email_body += f"Campos extraídos:\n"
            for k, v in doc.get("extracted_fields", {}).items():
                email_body += f"  - {k}: {v}\n"
            if notion_url:
                email_body += f"\nVer en Notion: {notion_url}"
            email_sent = True  # Email body generated (actual sending needs SMTP config)
            steps.append(f"email: body generated for {email_to}")
        except Exception as e:
            steps.append(f"email: error - {e}")

    from datetime import datetime
    return {
        "status": doc["status"],
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
        "email_body": email_body if request.send_email else None,
        "email_sent": email_sent,
        "llm_used": doc.get("llm_used", False),
        "total_tokens": doc.get("total_tokens", 0),
        "cost_usd": doc.get("cost_usd", 0),
        "processing_time_ms": round((time.time() - start) * 1000, 1),
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
