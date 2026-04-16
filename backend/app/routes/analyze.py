"""Analyze endpoint — upload files (PDF, Word, TXT), auto-generate questions, send results to Gmail.

This is the main user-facing endpoint for document analysis use cases.
"""

import io
import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from ..utils.run_tracker import start_run, record_step, complete_run

router = APIRouter(tags=["Analyze"])
logger = logging.getLogger(__name__)

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/csv": "csv",
    "text/markdown": "txt",
    "application/octet-stream": "auto",
}


async def _extract_text(file: UploadFile) -> tuple[str, str]:
    """Extract text content from uploaded file. Returns (text, detected_type)."""
    content_bytes = await file.read()

    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 10MB limit")

    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # PDF
    if ext == "pdf" or file.content_type == "application/pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip():
                raise ValueError("PDF has no extractable text (possibly scanned/image)")
            return text, "pdf"
        except ImportError:
            raise HTTPException(status_code=500, detail="PyPDF2 not installed")

    # Word DOCX
    if ext == "docx" or "wordprocessingml" in (file.content_type or ""):
        try:
            from docx import Document
            doc = Document(io.BytesIO(content_bytes))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return text, "docx"
        except ImportError:
            raise HTTPException(status_code=500, detail="python-docx not installed")

    # Plain text / CSV / Markdown
    try:
        text = content_bytes.decode("utf-8")
        return text, ext or "txt"
    except UnicodeDecodeError:
        text = content_bytes.decode("latin-1")
        return text, ext or "txt"


async def _generate_questions(content: str, doc_type: str, language: str) -> list[dict]:
    """Auto-generate relevant questions about the document using LLM."""
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_questions(doc_type, language)

    lang_label = "español" if language == "es" else "English"
    provider = "groq" if os.getenv("GROQ_API_KEY") else "anthropic"

    prompt = (
        f"Analiza el siguiente documento y genera exactamente 5 preguntas relevantes en {lang_label}. "
        f"Las preguntas deben cubrir: contenido clave, datos importantes, posibles acciones, "
        f"y verificaciones necesarias. Responde SOLO con JSON: "
        f'[{{"question": "...", "category": "key_info|action|verification|insight|summary"}}]\n\n'
        f"Documento (primeros 2000 chars):\n{content[:2000]}"
    )

    try:
        import httpx

        if provider == "groq":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 800,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 800,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                text = data["content"][0]["text"]

        import json
        # Extract JSON from response
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        logger.warning("Question generation failed: %s", e)

    return _fallback_questions(doc_type, language)


def _fallback_questions(doc_type: str, language: str) -> list[dict]:
    """Fallback questions when LLM is unavailable."""
    if language == "es":
        return [
            {"question": "¿Cuál es el propósito principal del documento?", "category": "summary"},
            {"question": "¿Qué datos clave se pueden extraer?", "category": "key_info"},
            {"question": "¿Se requiere alguna acción inmediata?", "category": "action"},
            {"question": "¿Hay información faltante o inconsistente?", "category": "verification"},
            {"question": "¿Cuáles son las conclusiones más importantes?", "category": "insight"},
        ]
    return [
        {"question": "What is the main purpose of this document?", "category": "summary"},
        {"question": "What key data can be extracted?", "category": "key_info"},
        {"question": "Are there any immediate actions required?", "category": "action"},
        {"question": "Is there missing or inconsistent information?", "category": "verification"},
        {"question": "What are the most important conclusions?", "category": "insight"},
    ]


async def _answer_questions(content: str, questions: list[dict], language: str) -> list[dict]:
    """Answer the generated questions using LLM."""
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return [{"answer": "LLM no disponible", "confidence": 0} for _ in questions]

    lang_label = "español" if language == "es" else "English"
    provider = "groq" if os.getenv("GROQ_API_KEY") else "anthropic"

    q_list = "\n".join(f"{i+1}. {q['question']}" for i, q in enumerate(questions))
    prompt = (
        f"Basándote en el siguiente documento, responde cada pregunta en {lang_label}. "
        f"Sé conciso pero preciso. Responde SOLO con JSON: "
        f'[{{"answer": "...", "confidence": 0.0-1.0}}]\n\n'
        f"Documento:\n{content[:3000]}\n\nPreguntas:\n{q_list}"
    )

    try:
        import httpx

        if provider == "groq":
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                        "max_tokens": 1500,
                    },
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1500,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                text = resp.json()["content"][0]["text"]

        import json
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        logger.warning("Question answering failed: %s", e)

    return [{"answer": "No se pudo generar respuesta", "confidence": 0} for _ in questions]


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(..., description="PDF, Word (.docx), or text file"),
    questions: Optional[str] = Form(None, description="Custom questions (comma-separated). If empty, auto-generates."),
    language: str = Form("es", description="Language: es or en"),
    send_email: bool = Form(True, description="Send results to Gmail"),
    email_to: Optional[str] = Form(None, description="Recipient email (defaults to GMAIL_USER)"),
    save_to_notion: bool = Form(True, description="Save results to Notion"),
):
    """Upload a file, analyze it, auto-generate Q&A, and send results to Gmail.

    Supports: PDF, Word (.docx), TXT, CSV, Markdown.
    """
    start = time.time()
    steps = []

    # Step 1: Extract text from file
    try:
        text, file_type = await _extract_text(file)
        steps.append(f"extract: success ({len(text)} chars, type: {file_type})")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to extract text")

    # Step 2: Document Intelligence
    try:
        from ..use_cases.document_intelligence.workflow import run_document_intelligence_workflow
        from ..use_cases.document_intelligence.schemas import DocumentIntelligenceInput

        doc_result = await run_document_intelligence_workflow(
            DocumentIntelligenceInput(content=text, filename=file.filename or "upload", language=language)
        )
        doc_data = doc_result.model_dump()
        steps.append(f"intelligence: {doc_data['status']} (type: {doc_data['document_type']})")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Document intelligence failed")

    # Step 3: Generate or parse questions
    if questions and questions.strip():
        q_list = [{"question": q.strip(), "category": "custom"} for q in questions.split(",") if q.strip()]
    else:
        q_list = await _generate_questions(text, doc_data["document_type"], language)
    steps.append(f"questions: {len(q_list)} generated")

    # Step 4: Answer questions
    answers = await _answer_questions(text, q_list, language)
    steps.append(f"answers: {len(answers)} generated")

    # Step 5: Save to Notion
    notion_url = None
    if save_to_notion:
        try:
            from ..integrations.notion.client import write_page
            title = f"[ANALYSIS] {file.filename or 'upload'}"
            body = f"Tipo: {doc_data['document_type']}\n"
            body += f"Resumen: {doc_data.get('summary', '')}\n\n"
            body += "Preguntas y Respuestas:\n"
            for i, q in enumerate(q_list):
                a = answers[i] if i < len(answers) else {"answer": "N/A"}
                body += f"Q: {q['question']}\nA: {a.get('answer', 'N/A')}\n\n"
            nr = await write_page(title=title, content=body)
            notion_url = nr.get("url") if nr["status"] == "success" else None
            steps.append(f"notion: {'success' if notion_url else 'failed'}")
        except Exception as e:
            steps.append(f"notion: error - {e}")

    # Step 6: Send email
    email_sent = False
    if send_email:
        try:
            from ..integrations.email.client import send_email as resend_email, build_analysis_email

            recipient = email_to or os.getenv("GMAIL_USER")
            if recipient:
                html = build_analysis_email(
                    file_name=file.filename or "upload",
                    document_type=doc_data["document_type"],
                    summary=doc_data.get("summary", ""),
                    extracted_fields=doc_data.get("extracted_fields", {}),
                    questions=q_list,
                    answers=answers,
                    notion_url=notion_url,
                    cost_usd=doc_data.get("cost_usd", 0),
                    total_tokens=doc_data.get("total_tokens", 0),
                )
                result = await resend_email(
                    to=recipient,
                    subject=f"[NexusForge] Análisis: {file.filename or 'documento'}",
                    html_body=html,
                )
                email_sent = result["status"] == "success"
                steps.append(f"email: {'success' if email_sent else result.get('message', 'failed')} -> {recipient}")
            else:
                steps.append("email: skipped (no recipient)")
        except Exception as e:
            steps.append(f"email: error - {e}")

    processing_time = round((time.time() - start) * 1000, 1)

    # Step 7: Persist to workflow_runs via run_tracker (best-effort)
    run_id = None
    try:
        run_id = await start_run(
            pipeline_name="analyze",
            trigger_type="api",
            metadata={"file": file.filename or "upload", "language": language},
        )
        agents = doc_data.get("agents_used", ["DocumentRAG", "Summarizer", "QAGenerator"])
        agent_count = max(len(agents), 1)
        for agent in agents:
            await record_step(
                run_id, agent, agent.lower(),
                tokens_used=doc_data.get("total_tokens", 0) // agent_count,
                cost_usd=doc_data.get("cost_usd", 0) / agent_count,
                duration_ms=int(processing_time) // agent_count,
            )
        await complete_run(
            run_id,
            status=doc_data["status"],
            total_tokens=doc_data.get("total_tokens", 0),
            total_cost_usd=float(doc_data.get("cost_usd", 0)),
            agents_used=doc_data.get("agents_used", []),
            notion_url=notion_url,
        )
    except Exception as e:
        logger.warning("analyze: run_tracker failed: %s", e)

    return {
        "status": doc_data["status"],
        "run_id": run_id,
        "file_name": file.filename,
        "file_type": file_type,
        "document_type": doc_data["document_type"],
        "summary": doc_data.get("summary", ""),
        "extracted_fields": doc_data.get("extracted_fields", {}),
        "questions": q_list,
        "answers": answers,
        "notion_url": notion_url,
        "email_sent": email_sent,
        "llm_used": doc_data.get("llm_used", False),
        "total_tokens": doc_data.get("total_tokens", 0),
        "cost_usd": doc_data.get("cost_usd", 0),
        "processing_time_ms": processing_time,
        "agents_used": doc_data.get("agents_used", []),
        "pipeline_steps": steps,
    }


@router.post("/analyze/text")
async def analyze_text(
    content: str = Form(..., description="Text content to analyze"),
    questions: Optional[str] = Form(None, description="Custom questions (comma-separated)"),
    language: str = Form("es"),
    send_email: bool = Form(True),
    email_to: Optional[str] = Form(None),
    save_to_notion: bool = Form(True),
):
    """Analyze raw text input (no file upload needed)."""
    start = time.time()
    steps = []

    if len(content.strip()) < 20:
        raise HTTPException(status_code=400, detail="Content too short (min 20 chars)")

    # Document Intelligence
    try:
        from ..use_cases.document_intelligence.workflow import run_document_intelligence_workflow
        from ..use_cases.document_intelligence.schemas import DocumentIntelligenceInput

        doc_result = await run_document_intelligence_workflow(
            DocumentIntelligenceInput(content=content, filename="text_input", language=language)
        )
        doc_data = doc_result.model_dump()
        steps.append(f"intelligence: {doc_data['status']}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Analysis failed")

    # Questions
    if questions and questions.strip():
        q_list = [{"question": q.strip(), "category": "custom"} for q in questions.split(",") if q.strip()]
    else:
        q_list = await _generate_questions(content, doc_data["document_type"], language)
    steps.append(f"questions: {len(q_list)}")

    # Answers
    answers = await _answer_questions(content, q_list, language)
    steps.append(f"answers: {len(answers)}")

    # Notion
    notion_url = None
    if save_to_notion:
        try:
            from ..integrations.notion.client import write_page
            title = f"[ANALYSIS] Text Input ({doc_data['document_type']})"
            body = f"Resumen: {doc_data.get('summary', '')}\n\n"
            for i, q in enumerate(q_list):
                a = answers[i] if i < len(answers) else {"answer": "N/A"}
                body += f"Q: {q['question']}\nA: {a.get('answer', 'N/A')}\n\n"
            nr = await write_page(title=title, content=body)
            notion_url = nr.get("url") if nr["status"] == "success" else None
            steps.append(f"notion: {'success' if notion_url else 'failed'}")
        except Exception as e:
            steps.append(f"notion: error - {e}")

    # Email
    email_sent = False
    if send_email:
        try:
            from ..integrations.email.client import send_email as resend_email, build_analysis_email
            recipient = email_to or os.getenv("GMAIL_USER")
            if recipient:
                html = build_analysis_email(
                    file_name="Text Input",
                    document_type=doc_data["document_type"],
                    summary=doc_data.get("summary", ""),
                    extracted_fields=doc_data.get("extracted_fields", {}),
                    questions=q_list,
                    answers=answers,
                    notion_url=notion_url,
                    cost_usd=doc_data.get("cost_usd", 0),
                    total_tokens=doc_data.get("total_tokens", 0),
                )
                result = await resend_email(
                    to=recipient,
                    subject=f"[NexusForge] Análisis de texto ({doc_data['document_type']})",
                    html_body=html,
                )
                email_sent = result["status"] == "success"
                steps.append(f"email: {'success' if email_sent else 'failed'}")
        except Exception as e:
            steps.append(f"email: error - {e}")

    processing_time = round((time.time() - start) * 1000, 1)

    # Persist to workflow_runs via run_tracker (best-effort)
    try:
        tracker_id = await start_run(
            pipeline_name="analyze-text",
            trigger_type="api",
            metadata={"language": language},
        )
        agents = doc_data.get("agents_used", ["DocumentRAG", "Summarizer", "QAGenerator"])
        agent_count = max(len(agents), 1)
        for agent in agents:
            await record_step(
                tracker_id, agent, agent.lower(),
                tokens_used=doc_data.get("total_tokens", 0) // agent_count,
                cost_usd=doc_data.get("cost_usd", 0) / agent_count,
                duration_ms=int(processing_time) // agent_count,
            )
        await complete_run(
            tracker_id,
            status=doc_data["status"],
            total_tokens=doc_data.get("total_tokens", 0),
            total_cost_usd=float(doc_data.get("cost_usd", 0)),
            agents_used=doc_data.get("agents_used", []),
            notion_url=notion_url,
        )
    except Exception as e:
        logger.warning("analyze-text: run_tracker failed: %s", e)

    return {
        "status": doc_data["status"],
        "document_type": doc_data["document_type"],
        "summary": doc_data.get("summary", ""),
        "extracted_fields": doc_data.get("extracted_fields", {}),
        "questions": q_list,
        "answers": answers,
        "notion_url": notion_url,
        "email_sent": email_sent,
        "total_tokens": doc_data.get("total_tokens", 0),
        "cost_usd": doc_data.get("cost_usd", 0),
        "processing_time_ms": processing_time,
        "pipeline_steps": steps,
    }


@router.get("/pipeline-runs")
async def get_all_pipeline_runs(
    pipeline: Optional[str] = Query(None, description="Filter by pipeline name"),
    limit: int = Query(20, ge=1, le=100),
):
    """List all persisted run history from workflow_runs (unified source)."""
    try:
        from ..utils.run_tracker import list_runs
        runs = await list_runs(pipeline_name=pipeline, limit=limit)
        for run in runs:
            run["id"] = str(run["id"])
            if run.get("created_at"):
                run["created_at"] = run["created_at"].isoformat()
        return {"status": "success", "runs": runs, "total": len(runs)}
    except Exception as e:
        return {"status": "error", "runs": [], "message": str(e)}
