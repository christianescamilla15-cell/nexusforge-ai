"""Conversational AI Wizard — streams responses with NexusForge domain knowledge."""

import json
import logging
import os
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/wizard", tags=["wizard-chat"])
logger = logging.getLogger(__name__)

NEXUSFORGE_SYSTEM_PROMPT = """You are NexusForge AI Architect — an expert automation designer.

## Your Role
You help users design, configure, and deploy business automations. You are confident, proactive, and show your reasoning.

## Your Knowledge
You have access to 24 specialized AI agents:
- **Triggers** (5): manual_trigger, schedule_trigger, webhook_trigger, email_trigger, file_trigger
- **Transforms** (14): classifier, extractor, summarizer, sentiment, translator, ocr, normalizer, analyzer, enricher, compliance, knowledge, router, validator, reporter
- **Actions** (6): email_action, slack_action, webhook_action, notion_action, drive_action, database_action

You know 6 swarm topologies: Sequential, Parallel, Hierarchical, Debate, Consensus, Adaptive.

## Automation Templates Available:
1. **Ticket Triage** — classify support tickets by urgency, route to teams, auto-respond
2. **Document Analysis** — extract data from PDFs/invoices, validate, store
3. **Email Auto-Responder** — classify email intent, search knowledge base, generate reply
4. **Report Generator** — gather data, analyze trends, generate executive summary
5. **Approval Workflow** — receive requests, validate rules, route for approval

## How You Respond
1. Be concise but helpful (2-4 sentences per response unless user asks for detail)
2. ALWAYS suggest specific agents and topology when discussing automations
3. Show reasoning: "I recommend the Classifier Agent because..."
4. Be proactive: "Since you need email processing, I suggest also adding the Sentiment Agent for tone detection"
5. Use the user's language (Spanish or English based on their input)
6. When the user describes an automation, respond with a structured suggestion:
   - Recommended agents and their roles
   - Pipeline flow (step by step)
   - Suggested input type and output destinations
   - Estimated processing time

## Important Rules
- You can ONLY use the agents and capabilities listed above
- Don't promise features that NexusForge doesn't have
- If unsure, ask clarifying questions
- Always end with a suggestion or question to keep the conversation moving
"""


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    language: str = "es"


@router.post("/chat")
async def wizard_chat(body: ChatRequest):
    """Stream a conversational response from the AI Wizard."""

    # Build messages for the LLM
    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    # Try Groq first (fast), fallback to simulated response
    groq_key = os.environ.get("GROQ_API_KEY", "")

    if groq_key:
        return await _stream_groq(groq_key, messages)
    else:
        return await _stream_simulated(messages, body.language)


async def _stream_groq(api_key: str, messages: list[dict]):
    """Stream response from Groq API."""
    import httpx

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "system", "content": NEXUSFORGE_SYSTEM_PROMPT}] + messages,
                        "temperature": 0.7,
                        "max_tokens": 1024,
                        "stream": True,
                    },
                    timeout=30,
                )

                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"
                        except json.JSONDecodeError:
                            pass

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.warning("Groq streaming failed: %s", e)
            yield f"data: {json.dumps({'type': 'text', 'content': f'Error connecting to AI service. Please try again.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_simulated(messages: list[dict], language: str):
    """Simulated streaming when no LLM API key is available."""
    import asyncio

    last_user_msg = ""
    for m in reversed(messages):
        if m["role"] == "user":
            last_user_msg = m["content"].lower()
            break

    # Generate contextual response based on keywords
    if any(w in last_user_msg for w in ["ticket", "soporte", "support", "clasificar"]):
        response = (
            "Para un sistema de triage de tickets, recomiendo este pipeline:\n\n"
            "1. **ExtractorAgent** - extrae datos clave del ticket\n"
            "2. **ClassifierAgent** - clasifica urgencia (critica/alta/media/baja)\n"
            "3. **RouterAgent** - asigna al equipo correcto\n"
            "4. **SummarizerAgent** - genera respuesta automatica\n"
            "5. **WebhookAgent** - notifica por Slack\n\n"
            "Topologia recomendada: **Sequential** para procesamiento ordenado.\n\n"
            "Quieres que configure esta automatizacion? Tambien puedo ajustar los niveles de urgencia o agregar mas agentes."
        )
    elif any(w in last_user_msg for w in ["factura", "invoice", "pdf", "documento", "document"]):
        response = (
            "Para procesamiento de documentos, sugiero:\n\n"
            "1. **OCRAgent** - extrae texto del PDF\n"
            "2. **ExtractorAgent** - identifica campos (vendor, monto, fecha)\n"
            "3. **NormalizerAgent** - estandariza formatos\n"
            "4. **ValidatorAgent** - verifica consistencia\n"
            "5. **ReporterAgent** - genera resumen\n\n"
            "Esto usa la topologia **Sequential** para procesamiento paso a paso. Necesitas que tambien guarde los resultados en Notion o los envie por email?"
        )
    elif any(w in last_user_msg for w in ["email", "correo", "responder", "reply"]):
        response = (
            "Para auto-respuesta de emails, recomiendo:\n\n"
            "1. **ClassifierAgent** - detecta intencion del email\n"
            "2. **KnowledgeAgent** - busca en tu base de conocimiento\n"
            "3. **SummarizerAgent** - genera respuesta personalizada\n"
            "4. **ValidatorAgent** - verifica calidad de la respuesta\n"
            "5. **EmailAction** - envia la respuesta\n\n"
            "Sugiero agregar **human-in-the-loop** para que puedas aprobar las respuestas antes de enviarlas. Te parece?"
        )
    elif any(w in last_user_msg for w in ["reporte", "report", "analytics", "resumen"]):
        response = (
            "Para generacion de reportes, el pipeline ideal es:\n\n"
            "1. **AnalyzerAgent** - identifica tendencias y anomalias\n"
            "2. **SentimentAgent** - analiza tono de feedback\n"
            "3. **EnricherAgent** - cruza datos de multiples fuentes\n"
            "4. **ReporterAgent** - compila reporte ejecutivo\n"
            "5. **ValidatorAgent** - verifica exactitud\n\n"
            "Puedo programarlo con **ScheduleTrigger** para que se ejecute cada lunes a las 9am. Que fuentes de datos necesitas conectar?"
        )
    elif any(w in last_user_msg for w in ["agente", "agent", "agents", "agentes"]):
        response = (
            "NexusForge tiene **24 agentes especializados** en 3 categorias:\n\n"
            "**Triggers (5):** manual, schedule, webhook, email, file - inician los flujos\n"
            "**Transforms (14):** classifier, extractor, summarizer, sentiment, translator, ocr, normalizer, analyzer, enricher, compliance, knowledge, router, validator, reporter\n"
            "**Actions (6):** email, slack, webhook, notion, drive, database\n\n"
            "Cada agente se puede combinar en pipelines usando 6 topologias diferentes. Quieres que te explique alguno en detalle?"
        )
    elif any(w in last_user_msg for w in ["topologia", "topology", "swarm", "patron"]):
        response = (
            "NexusForge soporta **6 topologias de swarm**:\n\n"
            "1. **Sequential** - pipeline ordenado paso a paso\n"
            "2. **Parallel** - multiples agentes trabajando simultaneamente\n"
            "3. **Hierarchical** - supervisor coordina sub-tareas\n"
            "4. **Debate** - agentes argumentan para mejorar resultados\n"
            "5. **Consensus** - multiples agentes votan decisiones\n"
            "6. **Adaptive** - selecciona topologia automaticamente segun complejidad\n\n"
            "Cual te interesa explorar? Puedo mostrarte un ejemplo practico."
        )
    else:
        if language == "es":
            response = (
                "Soy el Arquitecto AI de NexusForge. Puedo ayudarte a disenar automatizaciones para tu negocio.\n\n"
                "Puedo crear:\n"
                "- **Triage de tickets** - clasifica y responde automaticamente\n"
                "- **Analisis de documentos** - extrae datos de PDFs y facturas\n"
                "- **Auto-respuesta de emails** - clasifica y genera respuestas\n"
                "- **Generacion de reportes** - analiza datos y crea resumenes\n\n"
                "Que tipo de automatizacion necesitas? Describe tu caso de uso y te diseno el pipeline perfecto."
            )
        else:
            response = (
                "I'm NexusForge's AI Architect. I can help you design automations for your business.\n\n"
                "I can create:\n"
                "- **Ticket triage** - auto-classify and respond\n"
                "- **Document analysis** - extract data from PDFs and invoices\n"
                "- **Email auto-responder** - classify and generate replies\n"
                "- **Report generation** - analyze data and create summaries\n\n"
                "What kind of automation do you need? Describe your use case and I'll design the perfect pipeline."
            )

    async def generate():
        # Stream word-by-word for a more natural effect
        words = response.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else " " + word
            yield f"data: {json.dumps({'type': 'text', 'content': token})}\n\n"
            await asyncio.sleep(0.03)  # 30ms per word for streaming effect
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
