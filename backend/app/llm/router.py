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
# gemma4:4b — fast classification + routing (upgraded from gemma3:4b)
_GEMMA_AGENTS = {"RouterAgent", "ClassifierAgent", "SentimentAgent"}

# gemma4:27b — local reasoning for complex agents (MoE, thinking mode)
_REASONING_AGENTS = {"PlannerAgent", "CriticAgent", "JudgeAgent"}

# qwen2.5-coder:7b — structured JSON, code-like deterministic output
_QWEN_AGENTS = {
    "ExtractorAgent", "NormalizerAgent", "ValidatorAgent",
    "RepairAgent", "KnowledgeAgent",
}

# llama3.1:8b — general language, narrative, synthesis
_LLAMA_AGENTS = {
    "SummarizerAgent", "AnalyzerAgent", "TranslatorAgent",
    "EnricherAgent", "MonitorAgent", "OCRAgent",
    "SchedulerAgent", "ScraperAgent",
}

# Cloud-only agents: skip Ollama, go straight to Groq -> Claude
# (Planner/Critic moved to local reasoning with gemma4:27b)
_CLOUD_PREFERRED_AGENTS = {"ReporterAgent", "ResearcherAgent"}

# Claude-only agents: bypass Groq, use Claude directly for critical tasks
_CLAUDE_ONLY_AGENTS = {"ComplianceAgent"}

_AGENT_MODEL_MAP: dict[str, str] = {
    **{a: "gemma4:4b" for a in _GEMMA_AGENTS},
    **{a: "gemma4:27b" for a in _REASONING_AGENTS},
    **{a: "qwen2.5-coder:7b" for a in _QWEN_AGENTS},
    **{a: "llama3.1:8b" for a in _LLAMA_AGENTS},
}

# Models that support native thinking mode (Ollama returns thinking field)
_THINKING_MODELS = {"gemma4:27b", "deepseek-r1:8b"}

# Meta-orchestration agent model assignments (pipeline phases)
_META_AGENTS = {
    "MetaThinkAgent": "gemma3:4b",       # THINK phase (use gemma4:27b when available)
    "MetaBuildAgent": "qwen2.5-coder:7b", # BUILD phase
    "MetaDocumentAgent": "llama3.1:8b",    # DOCUMENT phase
    "MetaVerifyAgent": "deepseek-r1:8b",   # VERIFY phase
    "MetaPredictAgent": "gemma3:4b",       # PREDICT phase (fast)
    "FeaturePredictorAgent": "gemma3:4b",
    "ArchitectureReasonerAgent": "gemma3:4b",
    "SpecGeneratorAgent": "qwen2.5-coder:7b",
    "EndpointIntelligenceAgent": "qwen2.5-coder:7b",
    "FlowOptimizerAgent": "gemma3:4b",
}

_AGENT_MODEL_MAP.update(_META_AGENTS)

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
        # Predictive memory for smart pre-routing (lazy init)
        self._predictive = None

    def _get_predictive(self):
        if self._predictive is None:
            try:
                from app.memory.predictive import PredictiveMemory
                self._predictive = PredictiveMemory()
            except Exception:
                pass
        return self._predictive

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

        # Predictive pre-routing: skip Ollama if historical data shows high fallback
        predictive = self._get_predictive()
        if predictive and ollama_model and agent_name:
            try:
                if await predictive.should_preempt_fallback(agent_name, ollama_model):
                    logger.info(
                        "Predictive: skipping Ollama for %s (high fallback probability)",
                        agent_name,
                    )
                    provider_chain = [p for p in provider_chain if p.name != "ollama"]
                    if ctx and ctx.tracker:
                        await ctx.tracker.agent_event(
                            run_id=ctx.run_id, agent_name=agent_name,
                            event_type="predictive_skip_ollama", step_id=step_id,
                            message="Predictive memory recommended skipping Ollama",
                        )
            except Exception:
                pass  # Prediction failure should never block execution

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
        logger.error("All LLM providers failed for '%s': %s", agent_name, detail or "no providers available")
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
