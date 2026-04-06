"""Conversational AI Wizard — streams responses with visible thinking.

LLM Fallback Chain:
  1. deepseek-r1:8b (local via Ollama — native <think> reasoning)
  2. Groq llama-3.3-70b-versatile (free cloud — prompted reasoning)
  3. Claude API (paid — last resort)
"""

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
You help users design, configure, and deploy business automations. You show your reasoning step by step.

## Available Agents (24)
- **Triggers** (5): manual_trigger, schedule_trigger, webhook_trigger, email_trigger, file_trigger
- **Transforms** (14): classifier, extractor, summarizer, sentiment, translator, ocr, normalizer, analyzer, enricher, compliance, knowledge, router, validator, reporter
- **Actions** (6): email_action, slack_action, webhook_action, notion_action, drive_action, database_action

## Swarm Topologies (6)
Sequential, Parallel, Hierarchical, Debate, Consensus, Adaptive.

## Input Sources
text, file, form, drive, sheets, webhook, email, api

## Output Destinations
dashboard, email, slack, notion, drive, sheets, export, webhook

## How You Respond
1. Use the user's language (Spanish or English based on their input)
2. When the user describes an automation, produce a structured JSON workflow:
   ```json
   {
     "name": "Workflow Name",
     "description": "Brief description",
     "steps": [
       {"name": "step_1", "type": "agent_type", "depends_on": []},
       {"name": "step_2", "type": "agent_type", "depends_on": ["step_1"]}
     ],
     "input_type": "text|file|drive|sheets|webhook|email|api",
     "output_destinations": ["dashboard", "email"],
     "topology": "sequential|parallel|hierarchical",
     "estimated_tokens": 5000,
     "estimated_cost_usd": 0.003
   }
   ```
3. ALWAYS suggest specific agents and explain WHY you chose them
4. Be proactive: suggest improvements the user might not have thought of
5. For multi-output configs, specify different destinations for different data types
6. Keep responses concise but complete

## Important
- Reason through the problem before answering
- If using deepseek-r1, put your reasoning inside <think> tags
- Always end with a question or suggested next action
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


async def _stream_ollama(messages: list[dict]):
    """Stream from Ollama deepseek-r1:8b with native <think> support."""
    import httpx
    base = _get_ollama_url()

    async def generate():
        try:
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
                    in_think = False
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if not content:
                                continue

                            # Detect <think> tags for reasoning display
                            if "<think>" in content:
                                in_think = True
                                content = content.replace("<think>", "")
                                if content.strip():
                                    yield f"data: {json.dumps({'type': 'thinking', 'content': content})}\n\n"
                                continue
                            if "</think>" in content:
                                in_think = False
                                content = content.replace("</think>", "")
                                if content.strip():
                                    yield f"data: {json.dumps({'type': 'thinking', 'content': content})}\n\n"
                                yield f"data: {json.dumps({'type': 'thinking_done'})}\n\n"
                                continue

                            msg_type = "thinking" if in_think else "text"
                            yield f"data: {json.dumps({'type': msg_type, 'content': content})}\n\n"

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
                        "model": "claude-sonnet-4-20250514",
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


# ── Main endpoint with fallback chain ───────────────────────────────────────


@router.post("/chat")
async def wizard_chat(body: ChatRequest):
    """Stream AI Wizard response. Fallback: deepseek-r1 → Groq → Claude."""

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    # 1. Try local deepseek-r1:8b (native thinking)
    if await _check_ollama("deepseek-r1:8b"):
        logger.info("Wizard chat: using deepseek-r1:8b (local)")
        return await _stream_ollama(messages)

    # 2. Fallback to Groq (free cloud)
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        logger.info("Wizard chat: using Groq (cloud fallback)")
        return await _stream_groq(groq_key, messages)

    # 3. Last resort: Claude
    claude_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if claude_key:
        logger.info("Wizard chat: using Claude (paid fallback)")
        return await _stream_claude(claude_key, messages)

    # 4. No LLM available — return error
    async def no_llm():
        yield f"data: {json.dumps({'type': 'text', 'content': 'No AI model available. Start Ollama or configure GROQ_API_KEY.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'provider': 'none'})}\n\n"

    return StreamingResponse(
        no_llm(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
