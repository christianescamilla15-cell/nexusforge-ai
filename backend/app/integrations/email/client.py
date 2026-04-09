"""Email integration via Resend API.

Sends analysis results and notifications to Gmail.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    from_address: Optional[str] = None,
) -> dict:
    """Send an email via Resend API."""
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.warning("Email service not configured (missing RESEND_API_KEY)")
        return {"status": "not_configured", "message": "Set RESEND_API_KEY env var"}

    sender = from_address or "NexusForge AI <onboarding@resend.dev>"

    payload = {
        "from": sender,
        "to": [to],
        "subject": subject,
        "html": html_body,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        logger.info("Email sent to %s (id: %s)", to, data.get("id"))
        return {"status": "success", "email_id": data.get("id"), "to": to}
    except httpx.HTTPStatusError as e:
        logger.error("Resend API error: %s - %s", e.response.status_code, e.response.text)
        return {"status": "error", "message": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        logger.exception("Failed to send email")
        return {"status": "error", "message": str(e)}


def build_analysis_email(
    file_name: str,
    document_type: str,
    summary: str,
    extracted_fields: dict,
    questions: list[dict],
    answers: list[dict],
    notion_url: Optional[str] = None,
    cost_usd: float = 0.0,
    total_tokens: int = 0,
) -> str:
    """Build HTML email with analysis results."""
    fields_html = ""
    for k, v in extracted_fields.items():
        val = v if isinstance(v, str) else ", ".join(v) if isinstance(v, list) else str(v)
        fields_html += f"<tr><td style='padding:6px 12px;border:1px solid #e2e8f0;font-weight:600'>{k}</td><td style='padding:6px 12px;border:1px solid #e2e8f0'>{val}</td></tr>"

    qa_html = ""
    for i, q in enumerate(questions):
        answer = answers[i] if i < len(answers) else {"answer": "Sin respuesta"}
        qa_html += f"""
        <div style='margin-bottom:16px;padding:12px;background:#f8fafc;border-radius:8px;border-left:4px solid #3b82f6'>
            <p style='margin:0 0 8px;font-weight:600;color:#1e293b'>Q: {q.get('question', '')}</p>
            <p style='margin:0;color:#475569'>A: {answer.get('answer', '')}</p>
        </div>"""

    notion_link = f"<a href='{notion_url}' style='color:#3b82f6'>Ver en Notion</a>" if notion_url else "N/A"

    return f"""
    <div style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;max-width:640px;margin:0 auto;color:#1e293b'>
        <div style='background:linear-gradient(135deg,#0f172a,#1e40af);padding:24px;border-radius:12px 12px 0 0'>
            <h1 style='margin:0;color:#fff;font-size:20px'>NexusForge AI — Analisis Completado</h1>
            <p style='margin:4px 0 0;color:#93c5fd;font-size:14px'>{file_name}</p>
        </div>
        <div style='padding:24px;background:#fff;border:1px solid #e2e8f0'>
            <div style='display:flex;gap:12px;margin-bottom:20px'>
                <span style='background:#dbeafe;color:#1e40af;padding:4px 12px;border-radius:20px;font-size:13px'>
                    {document_type.upper()}
                </span>
                <span style='background:#f0fdf4;color:#166534;padding:4px 12px;border-radius:20px;font-size:13px'>
                    {total_tokens} tokens - ${cost_usd:.4f}
                </span>
            </div>

            <h2 style='font-size:16px;margin:0 0 8px;color:#334155'>Resumen</h2>
            <p style='color:#475569;line-height:1.6'>{summary}</p>

            <h2 style='font-size:16px;margin:20px 0 8px;color:#334155'>Campos Extraidos</h2>
            <table style='width:100%;border-collapse:collapse;font-size:14px'>
                {fields_html or "<tr><td style='padding:6px 12px;color:#94a3b8'>Sin campos extraidos</td></tr>"}
            </table>

            <h2 style='font-size:16px;margin:20px 0 12px;color:#334155'>Preguntas y Respuestas</h2>
            {qa_html or "<p style='color:#94a3b8'>Sin preguntas generadas</p>"}

            <div style='margin-top:20px;padding:12px;background:#f1f5f9;border-radius:8px;font-size:13px;color:#64748b'>
                Notion: {notion_link}
            </div>
        </div>
        <div style='padding:12px;text-align:center;font-size:12px;color:#94a3b8'>
            Generado por NexusForge AI - Pipeline de Document Intelligence
        </div>
    </div>"""
