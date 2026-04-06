"""Multi-provider LLM router with per-agent model mapping and automatic fallback.

Fallback chain for all agents:
  1. Ollama (local GPU)  — free, ~20 t/s, requires PC on
  2. Groq               — free tier (14k req/day), cloud
  3. Claude             — paid, last resort

Per-agent local model assignment:
  gemma3:4b          → fast classification tasks (Router, Classifier, Sentiment)
  qwen2.5-coder:7b   → structured JSON output (Extractor, Normalizer, Validator, Repair, Knowledge)
  llama3.1:8b        → general language (Summarizer, Analyzer, Translator, Enricher, Monitor, OCR)

Cloud-only agents (skip Ollama, need 70B+ reasoning):
  PlannerAgent, ReporterAgent, ResearcherAgent, CriticAgent → Groq → Claude
  ComplianceAgent → Claude directly (regulatory/PII critical)
"""

import time
import logging
from collections import deque

from app.llm.provider import LLMResponse
from app.llm.groq_provider import GroqProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.token_tracker import calculate_cost
from app.domain.tracking.events import ExecutionContext

logger = logging.getLogger(__name__)

# ── Per-agent local model map ────────────────────────────────────────────────
# gemma3:4b — lightweight, fast classification
_GEMMA_AGENTS = {"RouterAgent", "ClassifierAgent", "SentimentAgent"}

# qwen2.5-coder:7b — structured JSON, code-like deterministic output
_QWEN_AGENTS = {
    "ExtractorAgent", "NormalizerAgent", "ValidatorAgent",
    "RepairAgent", "KnowledgeAgent",
}

# llama3.1:8b — general language, narrative, synthesis
_LLAMA_AGENTS = {
    "SummarizerAgent", "AnalyzerAgent", "TranslatorAgent",
    "EnricherAgent", "MonitorAgent", "OCRAgent",
}

# Cloud-only agents: skip Ollama entirely, go straight to Groq → Claude
_CLOUD_PREFERRED_AGENTS = {
    "PlannerAgent", "ReporterAgent", "ResearcherAgent", "CriticAgent",
}

# Claude-only agents: bypass Groq, use Claude directly for critical tasks
_CLAUDE_ONLY_AGENTS = {"ComplianceAgent"}

_AGENT_MODEL_MAP: dict[str, str] = {
    **{a: "gemma3:4b" for a in _GEMMA_AGENTS},
    **{a: "qwen2.5-coder:7b" for a in _QWEN_AGENTS},
    **{a: "llama3.1:8b" for a in _LLAMA_AGENTS},
}

# ── Circuit breaker settings ─────────────────────────────────────────────────
_CB_ERROR_THRESHOLD = 3
_CB_WINDOW_SECONDS = 60
_CB_COOLDOWN_SECONDS = 30


class _CircuitBreaker:
    def __init__(self):
        self._errors: deque[float] = deque()
        self._open_until: float = 0.0

    def record_error(self):
        now = time.monotonic()
        self._errors.append(now)
        cutoff = now - _CB_WINDOW_SECONDS
        while self._errors and self._errors[0] < cutoff:
            self._errors.popleft()
        if len(self._errors) >= _CB_ERROR_THRESHOLD:
            self._open_until = now + _CB_COOLDOWN_SECONDS
            logger.warning("Circuit breaker tripped — cooldown %ds", _CB_COOLDOWN_SECONDS)

    def is_open(self) -> bool:
        return time.monotonic() < self._open_until

    def reset(self):
        self._errors.clear()
        self._open_until = 0.0


class LLMRouter:
    """Route LLM calls to the right model per agent with automatic fallback."""

    def __init__(self):
        self._ollama = OllamaProvider()
        self._groq = GroqProvider()
        self._claude = ClaudeProvider()
        self._breakers: dict[str, _CircuitBreaker] = {
            "ollama": _CircuitBreaker(),
            "groq": _CircuitBreaker(),
            "claude": _CircuitBreaker(),
        }

    def _build_provider_chain(self, agent_name: str) -> list:
        """Return ordered provider list based on agent type."""
        # Claude-only: skip everything else
        if agent_name in _CLAUDE_ONLY_AGENTS:
            return [self._claude]

        # Cloud-preferred: skip Ollama, go Groq → Claude
        if agent_name in _CLOUD_PREFERRED_AGENTS:
            return [self._groq, self._claude]

        # Everyone else: Ollama → Groq → Claude
        return [self._ollama, self._groq, self._claude]

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        agent_name: str = "",
        ctx: ExecutionContext = None,
        step_id: str = None,
    ) -> LLMResponse:
        """Route call through provider chain. Respects per-agent model map and circuit breakers."""

        # Set Ollama model based on agent
        ollama_model = _AGENT_MODEL_MAP.get(agent_name)
        if ollama_model:
            self._ollama.set_model(ollama_model)

        provider_chain = self._build_provider_chain(agent_name)
        errors = []

        for provider in provider_chain:
            if not provider.is_available():
                continue

            breaker = self._breakers[provider.name]
            if breaker.is_open():
                logger.info("Skipping %s (circuit open) for agent %s", provider.name, agent_name)
                if ctx and ctx.tracker:
                    await ctx.tracker.agent_event(
                        run_id=ctx.run_id,
                        agent_name=provider.name,
                        event_type="circuit_breaker_open",
                        step_id=step_id,
                        message=f"Circuit breaker open for {provider.name}, skipping",
                    )
                continue

            try:
                response = await provider.chat(messages, temperature, max_tokens)
                breaker.reset()
                response.cost_usd = calculate_cost(
                    response.provider, response.tokens_input, response.tokens_output
                )
                if provider.name != "ollama":
                    logger.info(
                        "Agent '%s' routed to %s (Ollama unavailable)",
                        agent_name, provider.name,
                    )
                return response

            except Exception as exc:
                logger.warning("Provider %s failed for agent %s: %s", provider.name, agent_name, exc)
                breaker.record_error()
                errors.append((provider.name, exc))

                # Track fallback event
                next_available = [
                    p.name for p in provider_chain
                    if p.name != provider.name
                    and p.is_available()
                    and not self._breakers[p.name].is_open()
                ]
                if ctx and ctx.tracker and next_available and step_id:
                    await ctx.tracker.fallback_recorded(
                        step_id=step_id,
                        from_provider=provider.name,
                        to_provider=next_available[0],
                    )

        detail = "; ".join(f"{n}: {e}" for n, e in errors)
        raise RuntimeError(
            f"All LLM providers failed for agent '{agent_name}' — {detail}"
            if detail else f"No LLM providers available for agent '{agent_name}'"
        )


# Module-level singleton
_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
