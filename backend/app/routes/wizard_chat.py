"""Conversational AI Wizard — streams responses with visible thinking.

LLM Fallback Chain:
  1. deepseek-r1:8b (local via Ollama — native <think> reasoning)
  2. Groq llama-3.3-70b-versatile (free cloud — prompted reasoning)
  3. Claude API (paid — last resort)
"""

import json
import logging
import os
import re

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


NEXUSFORGE_ARCHITECTURAL_SYSTEM_PROMPT = """You are NexusForge AI Architect — invoked when the user provides a structured, multi-requirement workflow specification (numbered lists, bulleted plans, code blocks, or prompts >500 characters).

## CRITICAL: NEVER WIZARD-MODE THIS
The user already gave you the full plan. Do NOT respond with "what's the first thing you want to do?" — that discards their input. Analyze ALL requirements at once and return a complete plan.

## YOU HAVE TOOLS — USE THEM TO GROUND
You have access to NexusForge self-knowledge tools (list_agents, list_synth_templates, list_api_routes, describe_memory_tiers, describe_self_healing, describe_recent_security_fixes). USE them when you need to reference specific capabilities, instead of reciting from memory. They return ground-truth from the running platform, including post-2026-05-02 fixes. Calling 1-3 tools per architectural plan is normal; calling zero usually means you're guessing. NEVER fabricate agent names, route paths, or fix commit hashes — call the tool.

## YOUR JOB
Given a requirements specification, return:

1. **Acknowledgment** — 1 sentence confirming what was understood (no fluff)
2. **Plan** — enumerated steps mapped to existing NexusForge capabilities. Reference real agent / module / endpoint names. Use a markdown table if it helps.
3. **Capabilities used** — explicit list of which agents / modules / endpoints will run each step
4. **Open architectural questions** — 1 to 3 specific decisions that genuinely need user input (auth model, tenant partitioning strategy, schedule semantics). NEVER ask trivia. NEVER ask "where does the data come from" if the user already told you.
5. **Schedule + execution mode** — confirm any cron/dry-run/threshold the user mentioned
6. **Go/no-go question** at the very end — ONE sentence asking permission to create the workflow

## NEXUSFORGE CAPABILITIES YOU MAY MAP TO

### Agents (24 total — pick the right ones, do NOT list all)
- Classification: classifier, sentiment, router
- Extraction: extractor, ocr, knowledge, enricher
- Generation: summarizer, reporter, translator, normalizer
- Validation: validator, compliance, analyzer
- Refactor engine modules: ingest (10 langs → DAG), analyze (csharp_analyzer detects SQL injection / creds / god classes / auth gaps), csharp_fixer (advisory-only since 2026-05-02 — emits @param rewrite + TODO comment but does NOT bind the parameter; flag advisory_only=True in fix dicts), batch_pipeline (4 parallel workers, per-file rollback NOT transactional), pii_scan (25 PII types), db_integrity (FK + PII columns), test_gen (pytest/xUnit/Jest), cicd_gen (.NET + Python), rpa_scan, multi_repo, pr_gen
- Security: Mythos owner-only (X-Mythos-Key derived from JWT_SECRET) — 9 scan categories: secrets, auth, injection, crypto, config, rate_limit, data, deps, frontend. Use /api/mythos/scan or /api/mythos/scan/{category}; /api/mythos/scan/diff for delta vs prior run
- Platform synthesizer: /api/platform-synth/{chat,templates,build} — 7 templates (FastAPI+React+Postgres, Express+Next+Postgres, Django+Postgres, Go+Gin+Postgres, Rails, Phoenix, Spring Boot). build flags: git_init, github_repo_create, mythos_preflight

### Memory tiers (5)
- Working: in-process dict (per-execution scratch)
- Episodic: Redis 30d TTL + MongoDB rich queries (cross-session events)
- Semantic: pgvector embeddings (similarity recall)
- Regressive: anomaly detection on metrics windows
- Predictive: execution forecast (recommendation: proceed / fallback / skip)

### Self-healing strategies (5)
retry → skip → repair → escalate → fallback. FallbackStrategy is **tenant-scoped** post-2026-05-02 (JOINs workflow_runs.user_id; will not return another tenant's results). Self-healing has 120s timeout total.

### Workflows + Executions + Audit
- /api/workflows/* CRUD (Pydantic body uses `dag_definition` with steps: [{name, type, config, depends_on}], NOT `spec`)
- /api/executions/* trigger; WebSocket at /api/executions/ws/{run_id} requires `?token=<JWT>` query param + ownership check (1008 close on auth/owner failure)
- /api/automations/* publish + schedule cron + webhook trigger
- /api/audit/* compliance log + entity trail + CSV export
- /api/executions-db/* DB-backed timeline + checkpoints (use this for "reproducible 6 months" requirements)

### Multi-tenant
- request.state.org_id (set by TenantMiddleware; application-layer)
- Refresh tokens + API keys carry org_id claim (post-2026-05-02 commit 2cadb56)
- DB-layer RLS via SET LOCAL is currently a documented no-op (Tier 3); routes filter org_id explicitly via WHERE clauses
- For strict tenant isolation: scope every DB query by org_id at the application layer

### LLM routing (24-agent fanout)
- Per-agent model selection: gemma → classification, qwen → code, llama → language, haiku → fast cloud
- Fallback chain: Ollama → Haiku → Groq → Claude (with prompt caching)
- Architectural prompts (this mode) skip Groq → Claude direct (post-2026-05-03 commit faebd1f)

## OUTPUT STYLE
- Use markdown headers, tables, code blocks. The user knows the platform — write at engineer level.
- Be specific: cite file paths, route names, agent identifiers, schemas.
- Keep prose terse. Lists and tables over paragraphs.
- For each step, name the capability it maps to. If a requirement does NOT map to any existing capability, flag it explicitly: "Step N — gap: requires new module" — and propose synthesizer or a focused refactor.
- Multi-tenant requirements: ALWAYS call out org_id handling per step.
- Reproducibility / compliance requirements: cite /api/executions-db/* + /api/audit/*.

## DO NOT
- Fabricate capabilities. Only reference the inventory above.
- Show JSON workflow structures inline unless the user asks.
- List all 24 agents — only the ones relevant to this plan.
- End with "what's the first thing?" or any open-ended wizard question.
- Pretend the smoke harness, the RLS layer, or AST-backed C# fixer are working — they're not yet (Tier 2/3 backlog).
"""


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
            # M-1 (2026-04-25): emit only the exception class name to
            # the client; full exception (incl. URLs/credentials in
            # httpx errors) is captured by the logger above.
            yield f"data: {json.dumps({'type': 'error', 'content': type(e).__name__})}\n\n"

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
            # M-1 (2026-04-25): emit only the exception class name to
            # the client; full exception (incl. URLs/credentials in
            # httpx errors) is captured by the logger above.
            yield f"data: {json.dumps({'type': 'error', 'content': type(e).__name__})}\n\n"

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
            # M-1 (2026-04-25): emit only the exception class name to
            # the client; full exception (incl. URLs/credentials in
            # httpx errors) is captured by the logger above.
            yield f"data: {json.dumps({'type': 'error', 'content': type(e).__name__})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'provider': 'groq-error'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Self-knowledge tools for architectural mode (Tier 3 #2, 2026-05-03) ──
#
# These give Claude a way to GROUND its plan in actual NexusForge
# capabilities instead of relying on a static inventory baked into the
# system prompt (which can grow stale and which the model has been seen
# to fabricate around). Each tool returns a string that Claude consumes
# as `tool_result` content. Handlers are deliberately synchronous +
# self-contained — no DB calls, no LLM calls — so a single architectural
# turn never blocks on side effects.
#
# Future expansion: replace static returns with live queries (agent
# registry DB, route inspection of include_router calls, recent commit
# log via gh api, etc.). For MVP the data is the same content that used
# to live inline in NEXUSFORGE_ARCHITECTURAL_SYSTEM_PROMPT; pulling it
# out lets Claude pay only for what it actually references.

ARCHITECTURAL_TOOLS = [
    {
        "name": "list_agents",
        "description": "List all 24 NexusForge agents grouped by category (classification, extraction, generation, validation, refactor-engine modules). Call this when mapping workflow steps to specific agents.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_synth_templates",
        "description": "List the 7 platform synthesizer templates with their stacks and build flags. Call this when the user wants a new project generated.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_api_routes",
        "description": "List backend API routes grouped by surface. Useful for grounding endpoint references in plans (e.g. /api/workflows/, /api/executions/, /api/mythos/scan/).",
        "input_schema": {
            "type": "object",
            "properties": {
                "surface": {
                    "type": "string",
                    "description": "Optional surface filter — one of: auth, workflows, executions, refactor, mythos, audit, automations, platform-synth. Omit to return all surfaces.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "describe_memory_tiers",
        "description": "Return the 5 memory tiers (working, episodic, semantic, regressive, predictive) with their backends, TTLs, and use cases.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "describe_self_healing",
        "description": "Return the 5 self-healing strategies (retry, skip, repair, escalate, fallback), their order of escalation, the 120s timeout, and the post-2026-05-02 tenant-scoping fix.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "describe_recent_security_fixes",
        "description": "Return a summary of recent (post-2026-05-02 triangulation) security fixes the platform has shipped: WebSocket auth+ownership, FallbackStrategy tenant scope, refresh-token GETDEL atomic, TenantMiddleware honest no-op, csharp_fixer advisory-only marker, etc. Useful when the user references known limitations.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


def _tool_list_agents(_args: dict) -> str:
    return """## NexusForge agents (24 total)

**Classification**: classifier, sentiment, router
**Extraction**: extractor, ocr, knowledge, enricher
**Generation**: summarizer, reporter, translator, normalizer
**Validation**: validator, compliance, analyzer

**Refactor engine modules** (called as agents in workflows):
- ingest — clones repo, detects 10 langs, builds dependency graph DAG
- analyze — csharp_analyzer detects SQL injection / creds / god classes / auth gaps
- csharp_fixer — ⚠ ADVISORY-ONLY since 2026-05-02 (commit 5e7aa78). Emits `@param` rewrite + TODO comment, does NOT bind the parameter. Each fix dict carries advisory_only=True. Use for triage; do NOT auto-merge.
- batch_pipeline — 4 parallel workers, per-file rollback (NOT transactional batch rollback)
- pii_scan — 25 PII types
- db_integrity — FK + PII columns
- test_gen — pytest / xUnit / Jest
- cicd_gen — GitHub Actions for .NET + Python
- rpa_scan — Playwright selector stability
- multi_repo — parallel ingestion of 5+ repos
- pr_gen — auto-branch + commit + PR body with metrics
"""


def _tool_list_synth_templates(_args: dict) -> str:
    return """## Platform Synthesizer templates (7)

| Template | Stack | Build flags |
|---|---|---|
| FastAPI+React | Python 3.12 + React 18 + Postgres | git_init, github_repo_create, mythos_preflight |
| Express+Next | Node 20 + Next 14 + Postgres | same |
| Django | Python 3.12 + Postgres | same |
| Go+Gin | Go 1.22 + Postgres | same |
| Rails | Ruby 3.3 + Postgres | same |
| Phoenix | Elixir 1.16 + Postgres | same |
| Spring Boot | Java 21 + Postgres | same |

Endpoints: POST /api/platform-synth/chat, GET /api/platform-synth/templates, POST /api/platform-synth/build.

Mythos preflight: when build flag is set, runs full Mythos scan on the generated project. Currently does NOT gate the build — returns status="partial" with mythos_score even if findings are high. (Tracked as Tier 2/3.)
"""


def _tool_list_api_routes(args: dict) -> str:
    surface = (args.get("surface") or "").lower().strip()
    routes = {
        "auth": [
            "POST /api/auth/register",
            "POST /api/auth/login",
            "POST /api/auth/logout",
            "GET /api/auth/me",
            "POST /api/auth/refresh (refresh-token rotation; GETDEL atomic since 2026-05-02)",
            "POST /api/auth/oauth (Google)",
        ],
        "workflows": [
            "POST /api/workflows/ — body: WorkflowCreate {name, description, dag_definition: {steps: [{name, type, config, depends_on}]}} (NOT 'spec')",
            "GET /api/workflows/ — list with skip/limit",
            "GET /api/workflows/{id}",
            "PUT /api/workflows/{id}",
            "DELETE /api/workflows/{id}",
        ],
        "executions": [
            "POST /api/executions/ — trigger workflow run",
            "GET /api/executions/{run_id}",
            "WebSocket /api/executions/ws/{run_id}?token=<JWT> — auth+ownership enforced post-2026-05-02 (close 1008 on auth/owner fail)",
            "DELETE /api/executions/{run_id} — cancel/delete",
        ],
        "refactor": [
            "POST /api/refactor/ingest — body: IngestRequest {path, name?} (NOT 'source_path')",
            "POST /api/refactor/execute",
            "POST /api/refactor/triage",
            "POST /api/refactor/batch-remediate",
            "POST /api/refactor/analyze-csharp",
            "POST /api/refactor/fix-csharp",
            "POST /api/refactor/scan-pii, /scan-db, /scan-rpa, /scan-multilang",
            "POST /api/refactor/multi-repo",
            "POST /api/refactor/pr",
            "GET /api/refactor/status",
        ],
        "mythos": [
            "POST /api/mythos/scan — full 9-category scan (owner-only via X-Mythos-Key)",
            "POST /api/mythos/scan/{category} — category in: secrets, auth, injection, crypto, config, rate_limit, data, deps, frontend",
            "GET /api/mythos/scan/diff — delta vs prior run",
        ],
        "audit": [
            "GET /api/audit/ — paginated compliance log",
            "GET /api/audit/{entity}/{id} — entity trail",
            "GET /api/audit/export.csv — CSV export for retention",
        ],
        "automations": [
            "POST /api/automations/publish",
            "POST /api/automations/schedule — cron-based",
            "POST /api/automations/webhook/{id} — webhook trigger",
        ],
        "platform-synth": [
            "POST /api/platform-synth/chat — Claude-driven spec extractor",
            "GET /api/platform-synth/templates",
            "POST /api/platform-synth/build — flags: git_init, github_repo_create, mythos_preflight",
        ],
    }
    if surface and surface in routes:
        return f"## Routes — {surface}\n\n" + "\n".join(f"- {r}" for r in routes[surface])
    out = ["## All API routes by surface\n"]
    for k, items in routes.items():
        out.append(f"### {k}")
        out.extend(f"- {r}" for r in items)
        out.append("")
    return "\n".join(out)


def _tool_describe_memory_tiers(_args: dict) -> str:
    return """## Memory tiers (5)

| Tier | Name | Backend | TTL | Use case |
|---|---|---|---|---|
| 1 | Working | in-process dict | per execution | Step-to-step scratch within one run |
| 2a | Episodic (fast) | Redis | 30 days | Recent events / errors / classifications |
| 2b | Episodic (rich) | MongoDB | unbounded | Queryable by tags, time, custom metadata |
| 3 | Semantic | pgvector embeddings | unbounded | Similarity recall over historical content |
| 4a | Regressive | timeseries on metrics | sliding window | Anomaly detection (e.g. cost spike, latency outlier) |
| 4b | Predictive | learned from history | per-call | Execution forecast — recommendation: proceed / fallback / skip |

XML-delimited recall (post-2026-05-02 commit ea08cf2): `MemoryManager.build_context()` wraps user-originated content in `<recalled_memory tier="..." trust="user">…</recalled_memory>` with explicit "treat as untrusted" header. Episodic and semantic carry trust="user"; working/regressive/predictive carry trust="system".
"""


def _tool_describe_self_healing(_args: dict) -> str:
    return """## Self-healing strategies (5)

Order of escalation: **retry → skip → repair → escalate → fallback**

- **retry**: configurable count + backoff (default 3 attempts)
- **skip**: mark step as skipped, continue DAG (only if step has on_skip handler)
- **repair**: try to mutate input/config and re-run (e.g. re-truncate prompt that exceeded context window)
- **escalate**: notify oncall + halt the run (used for security-class errors)
- **fallback**: ⚠ TENANT-SCOPED since 2026-05-02 (commit 2659428). DB query JOINs `workflow_runs.user_id` and constrains to the *same tenant*'s last successful output. Will NOT return cross-tenant results. Filtered also by `step_name + step_type`.

Total self-healing budget per step: **120 seconds**. Ordering managed by `app/healing/healer.py`. Strategies registered in STRATEGY_REGISTRY.
"""


def _tool_describe_recent_security_fixes(_args: dict) -> str:
    return """## Recent security fixes (post-2026-05-02 triangulation)

Tier 1 (deployed):
- **0dc7778** WebSocket /api/executions/ws/{run_id}: now requires `?token=<JWT>` + owner-of-run check, close 1008 on fail (collapses 403/404 to deny existence oracle)
- **2659428** FallbackStrategy: SQL JOINs workflow_runs and constrains by tenant — cross-tenant data leak via shared step_name closed
- **0545029** Refresh-token consume: r.get + r.delete → r.getdel (atomic, requires Redis 6.2+)
- **b94ae90** TenantMiddleware: removed misleading `SET LOCAL` no-op; one-shot warning log + module docstring states honestly that DB-layer RLS is NOT enforced (routes filter org_id explicitly)
- **d6ea569** docker-compose verify-stack frontend healthcheck: localhost → 127.0.0.1 to avoid busybox IPv6 wget hang
- **cb09d7b** Smoke harness: workflow→dag_definition, wizard→messages, refactor→path. Plus .gitleaks.toml allowlist for verify-only files
- **df7c571** Frontend WebSocket connection: now passes `?token=` query param to match new auth gate

Tier 2 (deployed):
- **2cadb56** Refresh tokens + API keys: now carry org_id claim (groundwork for real RLS)
- **3ffb9e3** Global exception handlers in main.py: 422/500 sanitized in prod (`{"detail":"Invalid request payload","request_id":"..."}`)
- **ea08cf2** XML-delimited memory recall + xml-escape user content: persistent prompt-injection surface closed
- **3fb97ea** New tenant-isolation smoke: 2-user round-trip cross-fetch, expects 403/404
- **5e7aa78** csharp_fixer marked advisory-only: every fix dict carries advisory_only=True; comments now scream "MUST add parameter binding manually"

Still PENDING (Tier 3 backlog):
- Per-request pinned DB connection (real RLS with SET LOCAL on a connection that survives the request)
- AST-backed C# fixer (replace regex transforms with Roslyn-style)
- Refactor smoke harness for the 3 newly-discovered failures (workflow has no /run endpoint, wizard chat returns SSE not JSON, refactor needs container-visible path)
- aios-kiro-master 1.0.1 republish with package_data fix
"""


# Map tool name → handler
_ARCH_TOOL_HANDLERS = {
    "list_agents": _tool_list_agents,
    "list_synth_templates": _tool_list_synth_templates,
    "list_api_routes": _tool_list_api_routes,
    "describe_memory_tiers": _tool_describe_memory_tiers,
    "describe_self_healing": _tool_describe_self_healing,
    "describe_recent_security_fixes": _tool_describe_recent_security_fixes,
}


async def _claude_with_tools_streaming(api_key: str, messages: list[dict], system_prompt: str, max_tokens: int = 4096):
    """Async generator yielding SSE event dicts as the tool loop progresses.

    Tier 3 #4 (preview-during-reasoning, 2026-05-03): each tool call
    emits a 'thinking' event that the frontend renders in the live
    indicator, so the user sees what NexusForge is consulting in
    real time instead of staring at a blank panel for 10+ seconds.

    Event shapes yielded:
      {type: 'thinking', content: '...'}
        — emitted at start, between turns, and around each tool call
      {type: 'text', content: '...'}
        — emitted ONCE at the end with the final answer
      {type: 'done', provider: '...'}
        — emitted last, signals the stream is over

    On exception, yields {type: 'error', content: '<class>'} + done.
    """
    import httpx

    convo: list[dict] = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m["role"] in ("user", "assistant")
    ]

    MAX_TURNS = 6
    provider_label = "Claude (cloud, with tools)"
    final_text = ""

    yield {"type": "thinking", "content": "🧠 Analizando requerimientos…"}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            for turn in range(MAX_TURNS):
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-opus-4-7",
                        "max_tokens": max_tokens,
                        "system": system_prompt,
                        "messages": convo,
                        "tools": ARCHITECTURAL_TOOLS,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                payload = response.json()
                stop_reason = payload.get("stop_reason")
                content_blocks = payload.get("content", [])

                convo.append({"role": "assistant", "content": content_blocks})

                if stop_reason != "tool_use":
                    final_text = "".join(
                        b.get("text", "") for b in content_blocks if b.get("type") == "text"
                    )
                    break

                # Execute every tool_use block, surfacing each one to the
                # user as a thinking step before running the handler.
                tool_results: list[dict] = []
                tool_names_this_turn: list[str] = []
                for block in content_blocks:
                    if block.get("type") != "tool_use":
                        continue
                    name = block.get("name", "")
                    tool_id = block.get("id", "")
                    args = block.get("input", {}) or {}
                    tool_names_this_turn.append(name)

                    yield {
                        "type": "thinking",
                        "content": f"🔧 Consultando capacidad de NexusForge: `{name}`…",
                    }

                    handler = _ARCH_TOOL_HANDLERS.get(name)
                    if handler is None:
                        result_text = f"Tool '{name}' is not registered."
                    else:
                        try:
                            result_text = handler(args)
                        except Exception as exc:
                            logger.exception("architectural tool '%s' failed", name)
                            result_text = f"Tool '{name}' raised {type(exc).__name__}."

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result_text,
                    })

                convo.append({"role": "user", "content": tool_results})
                yield {
                    "type": "thinking",
                    "content": f"✅ Recibido ({len(tool_names_this_turn)} herramienta{'s' if len(tool_names_this_turn) != 1 else ''}). Tejiendo el plan…",
                }
            else:
                # MAX_TURNS exhausted without a final answer
                final_text = (
                    "Llegué al límite de iteraciones de herramientas sin "
                    "una respuesta final. Por favor reformula con menos "
                    "requerimientos por turno."
                )
                provider_label = "Claude (cloud, with tools — turn limit)"

        if final_text:
            yield {"type": "text", "content": final_text}
        yield {"type": "done", "provider": provider_label}
    except Exception as exc:
        logger.exception("Claude tool loop failed")
        yield {"type": "error", "content": type(exc).__name__}
        yield {"type": "done", "provider": "claude-tools-error"}


async def _stream_claude(api_key: str, messages: list[dict], system_prompt: str | None = None, max_tokens: int = 2048):
    """Stream from Claude API. Optional `system_prompt` overrides the
    default wizard prompt for architectural-mode dispatch
    (post-2026-05-03 commit). `max_tokens` is bumped for architectural
    plans which need room for full multi-section output.
    """
    import httpx

    system = system_prompt if system_prompt is not None else NEXUSFORGE_SYSTEM_PROMPT

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
                        "max_tokens": max_tokens,
                        "system": system,
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
            # M-1 (2026-04-25): emit only the exception class name to
            # the client; full exception (incl. URLs/credentials in
            # httpx errors) is captured by the logger above.
            yield f"data: {json.dumps({'type': 'error', 'content': type(e).__name__})}\n\n"
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


def _is_architectural_prompt(messages: list[dict]) -> bool:
    """Detect prompts that require deep architectural reasoning.

    Heuristics: large total text, multi-item numbered/bulleted lists,
    code blocks, or explicit multi-step structure. These prompts hit
    the failure mode discovered in the 2026-05-03 stress test
    (12-requirement workflow → Groq llama-3.3-70b → "what's first?"
    wizard reply that discarded the structured input). Architectural
    prompts skip Groq and route directly to Claude/Haiku, which can
    plan over the full requirement set instead of collapsing into
    one-question-at-a-time wizard mode.

    Evaluates ONLY the latest user message (not the whole conversation
    history) so a casual follow-up after an architectural turn doesn't
    inherit the previous turn's complexity. Without this scoping, every
    message after a long prompt would route to Claude regardless of its
    own content — a false positive observed in the 2026-05-03 re-test.

    See: stress_test_2026_05_03_chat_orchestration_gap memory entry.
    """
    # Walk from the end to find the last user-role message. Anything
    # earlier (assistant turns, prior user turns) is conversation
    # history, not the current request being routed.
    latest_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            latest_user = str(m.get("content", ""))
            break
    if not latest_user:
        return False

    # Large prompt → architectural by length alone
    if len(latest_user) > 500:
        return True

    # 5+ numbered list items. Match either at line-start (multi-line
    # input) OR after whitespace (single-line input where the chat UI
    # collapsed newlines into spaces). 2026-05-03 re-test caught a
    # case where the UI sent "necesito: 1. foo 2. bar 3. baz 4. qux 5. quux"
    # as one line, so the line-start anchor never fired.
    numbered = len(re.findall(r"(?:^|\s)(\d+[.)\]])\s+\S", latest_user))
    if numbered >= 5:
        return True

    # 5+ bullets, same dual-mode matching
    bullets = len(re.findall(r"(?:^|\s)([-*•])\s+\S", latest_user))
    if bullets >= 5:
        return True

    # Code block — almost always needs depth (debugging, design, refactor)
    if "```" in latest_user:
        return True

    return False


@router.post("/chat")
async def wizard_chat(body: ChatRequest, request: Request):
    """Stream AI Wizard response (builder).

    Default fallback chain: gemma4:27b -> deepseek-r1:8b -> Groq -> Claude.
    Gemma 4 and deepseek-r1 both support native thinking mode.

    For architectural prompts (long, structured, code-heavy) the chain
    skips Groq because llama-3.3-70b cannot reason over a 12-requirement
    plan as a unit — it falls back to wizard-mode "what's first?"
    responses that discard the input. Those prompts go directly to
    Claude (or, when Haiku routing is wired, Haiku 4.5 first).
    """
    from app.auth.rate_limit import check_rate_limit
    await check_rate_limit(request)

    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    architectural = _is_architectural_prompt(messages)

    # Architectural fast-path: jump to Claude with a planning-mode system
    # prompt that forbids wizard-style "what's first?" responses, AND
    # give the model self-knowledge tools (Tier 3 #2, 2026-05-03) so it
    # grounds plans in actual platform capabilities instead of fabricating.
    # If Claude isn't configured we fall through to the normal chain
    # so the request still gets answered (best effort over silent fail).
    if architectural:
        claude_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if claude_key:
            logger.info(
                "Wizard chat: architectural prompt detected (len=%d), using Claude with tools (streaming)",
                sum(len(str(m.get("content", ""))) for m in messages),
            )

            # Stream tool-loop progress directly to the client. Each
            # tool call surfaces as a `thinking` event the frontend
            # already knows how to render in the live indicator —
            # closes Tier 3 #4 (preview-during-reasoning).
            async def _emit_arch():
                try:
                    async for event in _claude_with_tools_streaming(
                        claude_key,
                        messages,
                        system_prompt=NEXUSFORGE_ARCHITECTURAL_SYSTEM_PROMPT,
                        max_tokens=4096,
                    ):
                        yield f"data: {json.dumps(event)}\n\n"
                except Exception as exc:
                    logger.exception("Architectural streaming failed at outer wrapper")
                    yield f"data: {json.dumps({'type': 'error', 'content': type(exc).__name__})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'provider': 'claude-tools-error'})}\n\n"

            return StreamingResponse(
                _emit_arch(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        logger.warning("Wizard chat: architectural prompt but ANTHROPIC_API_KEY missing; falling through to default chain (Groq may give shallow response)")

    # 1. Try local gemma4:27b (best reasoning, native thinking)
    if await _check_ollama("gemma4:27b"):
        logger.info("Wizard chat: using gemma4:27b (local, thinking)")
        return await _stream_ollama_model(messages, "gemma4:27b", "Gemma 4 27B (local)")

    # 2. Try local deepseek-r1:8b (native thinking, lighter)
    if await _check_ollama("deepseek-r1:8b"):
        logger.info("Wizard chat: using deepseek-r1:8b (local)")
        return await _stream_ollama(messages)

    # 3. Fallback to Groq (free cloud) — fine for casual prompts only
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
