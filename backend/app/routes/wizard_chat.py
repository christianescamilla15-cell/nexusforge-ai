"""Conversational AI Wizard — streams responses with visible thinking.

LLM Fallback Chain:
  1. deepseek-r1:8b (local via Ollama — native <think> reasoning)
  2. Groq llama-3.3-70b-versatile (free cloud — prompted reasoning)
  3. Claude API (paid — last resort)
"""

import json
import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/wizard", tags=["wizard-chat"])
logger = logging.getLogger(__name__)

NEXUSFORGE_SYSTEM_PROMPT = """You are NexusForge AI Assistant — a friendly automation builder that guides users step by step.

## YOUR PERSONALITY
- You are warm, clear, and simple. Like a patient friend who builds things together.
- NEVER show JSON, code, technical details, or agent names to the user.
- NEVER dump everything at once. ONE question at a time.
- Speak like a human, not a machine. Short sentences. Use emojis sparingly.
- Use the user's language (Spanish if they write in Spanish, English if in English).

## HOW YOU WORK — GUIDED FLOW
You build automations through a step-by-step conversation. Each step = ONE message with ONE question.

### Step 1: UNDERSTAND
Ask what they want to automate in simple terms.
Example: "¡Hola! ¿Qué proceso te gustaría automatizar? Por ejemplo: procesar emails, analizar documentos, clasificar tickets..."

### Step 2: DATA SOURCE
Ask where comes the data.
Example: "Perfecto. ¿De dónde llegan esos datos? ¿Email, archivos en Drive, una plataforma como Zendesk, o los pegas manualmente?"

### Step 3: WHAT TO DO WITH IT
Ask what analysis/processing they need — but in simple terms, not agent names.
Example: "¿Qué necesitas que haga con cada ticket? Por ejemplo: clasificar por urgencia, extraer datos del cliente, analizar el tono, generar un resumen..."

### Step 4: WHERE TO SEND RESULTS
Ask where they want the results.
Example: "¿Dónde quieres recibir los resultados? Puedo enviarte: email, Slack, Google Sheets, Notion, Google Drive, o todo en el dashboard."

### Step 5: CUSTOMIZATION
Ask about colors, name, schedule.
Example: "Tu automatización está casi lista. ¿Cómo quieres llamarla? ¿Y qué color te gustaría para el dashboard?"

### Step 6: CONFIRM AND CREATE
Summarize in ONE simple paragraph (no tech details) and ask for confirmation.
Example: "Listo. Creé 'Triage de Tickets' — cada vez que llega un email, lo clasifico por urgencia, extraigo los datos del cliente, y te mando los urgentes a Slack y un resumen diario a tu email. ¿Lo publico?"

## RULES
- MAXIMUM 3 sentences per response + 1 question
- NEVER say "ClassifierAgent", "ExtractorAgent", etc. Say "clasifico", "extraigo", "analizo"
- NEVER show JSON or workflow structures to the user
- NEVER list all 24 agents or 6 topologies unless explicitly asked
- If the user asks a technical question, answer simply then return to the flow
- Build the JSON internally but NEVER show it
- Always end with a clear question to move to the next step
- If the user picks a quick action (Ticket Triage, Document Analysis, etc.), skip Step 1 and go to Step 2

## INTERNAL KNOWLEDGE (use but don't expose)
Agents: classifier, extractor, summarizer, sentiment, translator, ocr, normalizer, analyzer, enricher, compliance, knowledge, router, validator, reporter
Triggers: manual, schedule, webhook, email, file
Actions: email, slack, webhook, notion, drive, database
Topologies: Sequential, Parallel, Hierarchical, Debate, Consensus, Adaptive
Inputs: text, file, form, drive, sheets, webhook, email, api
Outputs: dashboard, email, slack, notion, drive, sheets, export, webhook
"""

GROQ_THINKING_PROMPT = """Before answering, reason step-by-step inside <think> tags.
Then provide your final answer. Example:
<think>
The user needs X, so I should consider agents A and B because...
</think>
[Your answer here]"""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    language: str = "es"


# ── Provider functions ──────────────────────────────────────────────────────


def _get_ollama_url() -> str:
    """Get Ollama URL — tunnel (cloud) or localhost."""
    return os.environ.get("OLLAMA_TUNNEL_URL", "http://localhost:11434")


async def _check_ollama(model: str = "deepseek-r1:8b") -> bool:
    """Quick health check: is Ollama running (local or via tunnel)?"""
    import httpx
    base = _get_ollama_url()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                if model in models:
                    logger.info("Ollama available at %s with %s", base, model)
                    return True
    except Exception:
        pass
    return False


async def _stream_ollama_model(messages: list[dict], model: str = "gemma4:27b", provider_label: str = "Gemma 4 27B (local)"):
    """Stream from any Ollama thinking model (gemma4, deepseek-r1, etc.)."""
    import httpx
    base = _get_ollama_url()

    async def generate():
        try:
            was_thinking = False
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{base}/api/chat",
                    json={"model": model, "messages": messages, "stream": True, "think": True},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        msg = chunk.get("message", {})
                        thinking = msg.get("thinking", "")
                        content = msg.get("content", "")
                        if thinking:
                            if not was_thinking:
                                was_thinking = True
                            yield f"data: {json.dumps({'type': 'thinking', 'content': thinking})}\n\n"
                        if content:
                            if was_thinking:
                                yield f"data: {json.dumps({'type': 'thinking_done'})}\n\n"
                                was_thinking = False
                            yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"

            if was_thinking:
                yield f"data: {json.dumps({'type': 'thinking_done'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'provider': provider_label})}\n\n"
        except Exception as e:
            logger.error("Ollama %s stream error: %s", model, e)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_ollama(messages: list[dict]):
    """Stream from Ollama deepseek-r1:8b with native <think> support."""
    import httpx
    base = _get_ollama_url()

    async def generate():
        try:
            was_thinking = False
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{base}/api/chat",
                    json={
                        "model": "deepseek-r1:8b",
                        "messages": [{"role": "system", "content": NEXUSFORGE_SYSTEM_PROMPT}] + messages,
                        "stream": True,
                        "options": {"temperature": 0.6, "num_ctx": 8192},
                    },
                    timeout=120,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            msg = chunk.get("message", {})

                            # Ollama deepseek-r1 sends thinking in a separate field
                            thinking = msg.get("thinking", "")
                            content = msg.get("content", "")

                            if thinking:
                                was_thinking = True
                                yield f"data: {json.dumps({'type': 'thinking', 'content': thinking})}\n\n"

                            if content:
                                # First content after thinking = transition
                                if was_thinking:
                                    yield f"data: {json.dumps({'type': 'thinking_done'})}\n\n"
                                    was_thinking = False
                                yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"

                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue

                yield f"data: {json.dumps({'type': 'done', 'provider': 'deepseek-r1:8b (local)'})}\n\n"
        except Exception as e:
            logger.warning("Ollama stream failed: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_groq(api_key: str, messages: list[dict]):
    """Stream from Groq with prompted <think> reasoning."""
    import httpx

    system = NEXUSFORGE_SYSTEM_PROMPT + "\n\n" + GROQ_THINKING_PROMPT

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
                        "messages": [{"role": "system", "content": system}] + messages,
                        "temperature": 0.7,
                        "max_tokens": 2048,
                        "stream": True,
                    },
                    timeout=30,
                )

                # Collect full response first, then parse <think> tags cleanly
                full_response = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_response += content
                        except json.JSONDecodeError:
                            pass

                # Parse <think> tags from complete response
                if "<think>" in full_response and "</think>" in full_response:
                    think_start = full_response.index("<think>") + 7
                    think_end = full_response.index("</think>")
                    thinking = full_response[think_start:think_end].strip()
                    answer = full_response[think_end + 8:].strip()

                    # Stream thinking
                    if thinking:
                        # Send in chunks for streaming effect
                        words = thinking.split(" ")
                        for i in range(0, len(words), 4):
                            chunk = " ".join(words[i:i+4])
                            yield f"data: {json.dumps({'type': 'thinking', 'content': chunk + ' '})}\n\n"
                        yield f"data: {json.dumps({'type': 'thinking_done'})}\n\n"

                    # Stream answer
                    if answer:
                        words = answer.split(" ")
                        for i in range(0, len(words), 3):
                            chunk = " ".join(words[i:i+3])
                            yield f"data: {json.dumps({'type': 'text', 'content': chunk + ' '})}\n\n"
                else:
                    # No think tags — stream everything as text
                    words = full_response.split(" ")
                    for i in range(0, len(words), 3):
                        chunk = " ".join(words[i:i+3])
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk + ' '})}\n\n"

                yield f"data: {json.dumps({'type': 'done', 'provider': 'Groq (llama-3.3-70b)'})}\n\n"
        except Exception as e:
            logger.warning("Groq streaming failed: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'provider': 'groq-error'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_claude(api_key: str, messages: list[dict]):
    """Stream from Claude API as last resort."""
    import httpx

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-opus-4-7",
                        "max_tokens": 2048,
                        "system": NEXUSFORGE_SYSTEM_PROMPT,
                        "messages": [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] in ("user", "assistant")],
                        "stream": True,
                    },
                    timeout=60,
                )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            if event.get("type") == "content_block_delta":
                                text = event.get("delta", {}).get("text", "")
                                if text:
                                    yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"
                        except json.JSONDecodeError:
                            pass

                yield f"data: {json.dumps({'type': 'done', 'provider': 'Claude (cloud)'})}\n\n"
        except Exception as e:
            logger.warning("Claude streaming failed: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'provider': 'claude-error'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Guide chat system prompt (simpler, always online) ───────────────────────

GUIDE_SYSTEM_PROMPT = """You are NexusForge AI Guide — a friendly assistant that helps users understand and navigate the platform.

## Your Role
- Answer questions about NexusForge AI features and capabilities
- Explain how automations, agents, and integrations work in simple terms
- Help users troubleshoot issues
- Guide users to the right section of the platform
- Be concise: 2-3 sentences max per response

## Platform Knowledge
NexusForge AI is an enterprise automation platform with:
- 24 AI agents that process data (classify, extract, analyze, summarize, etc.)
- 6 swarm topologies for complex workflows
- 12 integrations: Email, Slack, Notion, Google Drive, Google Sheets, Gmail, Webhook, External API, etc.
- AI Wizard that builds automations through conversation
- Dashboard with KPIs, execution history, and real-time monitoring
- Google OAuth + Stripe billing (Free/Pro/Team plans)

## Pages
- Home: AI chat to build automations conversationally
- Automations: list of your created automations
- AI Wizard: step-by-step automation builder
- Intelligence: document analysis hub
- Integrations: connect Email, Slack, Notion, Drive, etc.
- Settings: account, API URL, language, theme

## Rules
- Use the user's language (Spanish/English)
- Be warm and helpful
- Never show JSON or technical internals
- If they want to BUILD something, suggest going to the Home page chat
- Always be available — you run on cloud (Groq) 24/7
"""


# ── Main endpoints ──────────────────────────────────────────────────────────


@router.post("/chat")
async def wizard_chat(body: ChatRequest, request: Request):
    """Stream AI Wizard response (builder).

    Fallback chain: gemma4:27b -> deepseek-r1:8b -> Groq -> Claude.
    Gemma 4 and deepseek-r1 both support native thinking mode.
    """
    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    # 1. Try local gemma4:27b (best reasoning, native thinking)
    if await _check_ollama("gemma4:27b"):
        logger.info("Wizard chat: using gemma4:27b (local, thinking)")
        return await _stream_ollama_model(messages, "gemma4:27b", "Gemma 4 27B (local)")

    # 2. Try local deepseek-r1:8b (native thinking, lighter)
    if await _check_ollama("deepseek-r1:8b"):
        logger.info("Wizard chat: using deepseek-r1:8b (local)")
        return await _stream_ollama(messages)

    # 3. Fallback to Groq (free cloud)
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        logger.info("Wizard chat: using Groq (cloud fallback)")
        return await _stream_groq(groq_key, messages)

    # 4. Last resort: Claude
    claude_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if claude_key:
        logger.info("Wizard chat: using Claude (paid fallback)")
        return await _stream_claude(claude_key, messages)

    # 5. No LLM available
    async def no_llm():
        yield f"data: {json.dumps({'type': 'text', 'content': 'No AI model available. Start Ollama or configure GROQ_API_KEY.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'provider': 'none'})}\n\n"

    return StreamingResponse(
        no_llm(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/guide")
async def wizard_guide(body: ChatRequest, request: Request):
    """Stream guide chat response. Always uses Groq (online 24/7)."""
    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        return await _stream_groq_guide(groq_key, messages)

    # Fallback to Claude if no Groq
    claude_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if claude_key:
        return await _stream_claude(claude_key, messages)

    async def no_llm():
        yield f"data: {json.dumps({'type': 'text', 'content': 'Guide unavailable. Configure GROQ_API_KEY.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'provider': 'none'})}\n\n"

    return StreamingResponse(
        no_llm(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_groq_guide(api_key: str, messages: list[dict]):
    """Stream from Groq for the guide chat — no thinking, just direct responses."""
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
                        "messages": [{"role": "system", "content": GUIDE_SYSTEM_PROMPT}] + messages,
                        "temperature": 0.5,
                        "max_tokens": 512,
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

                yield f"data: {json.dumps({'type': 'done', 'provider': 'Groq Guide (24/7)'})}\n\n"
        except Exception as e:
            logger.warning("Groq guide failed: %s", e)
            yield f"data: {json.dumps({'type': 'text', 'content': 'Error connecting to guide. Try again.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'provider': 'error'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
