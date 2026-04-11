"""Abstract base agent class for all NexusForge agents."""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception

logger = logging.getLogger(__name__)

# Fast timeout for memory ops — don't let broken Redis block execution
_MEMORY_TIMEOUT = 2  # seconds

# Non-retryable exceptions (programming errors, not transient)
_NO_RETRY_TYPES = (ValueError, TypeError, KeyError, AttributeError, ImportError, SyntaxError)


def _should_retry(exc: BaseException) -> bool:
    """Retry everything except programming errors."""
    return not isinstance(exc, _NO_RETRY_TYPES)


def clean_llm_json(text: str) -> dict:
    """Clean LLM response and parse JSON. Handles markdown fences, extra text, etc."""
    t = text.strip()
    # Strip markdown code fences
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*\n?", "", t)
        t = re.sub(r"\n?```\s*$", "", t)
        t = t.strip()
    # Try direct parse first
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    # Try to extract JSON object from surrounding text
    match = re.search(r'\{.*\}', t, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Last resort: return fallback dict instead of crashing on plain string responses
    return {"raw_text": t[:500], "_parse_failed": True}


@dataclass
class AgentResult:
    """Unified result from any agent execution."""
    output: dict
    tokens_used: int = 0
    cost_usd: float = 0.0
    provider: str = "local"
    model: str = "none"


class BaseAgent(ABC):
    """Base class all agents must inherit from.

    Subclasses implement ``execute()``.  Callers should invoke ``run()``
    instead, which wraps ``execute()`` with memory recall/remember lifecycle.
    """

    name: str = "unnamed"
    agent_type: str = "unknown"
    description: str = ""

    def __init__(self) -> None:
        # Lazy import avoids circular deps and keeps memory optional
        from app.memory.manager import MemoryManager
        from app.agents.capabilities import AgentCapabilities
        from app.llm.local_client import LocalModelClient
        from app.llm.router import _AGENT_MODEL_MAP

        self._memory = MemoryManager()
        self.capabilities = AgentCapabilities(self.name)
        # Bind dedicated local model (falls back to router if Ollama is down)
        _local_model = _AGENT_MODEL_MAP.get(self.name, "qwen2.5-coder:7b")
        self._local = LocalModelClient(_local_model)

    async def run(self, input_data: dict, config: dict = None) -> AgentResult:
        """Public entrypoint: circuit breaker check → recall → execute → remember."""
        config = config or {}

        # --- circuit breaker: skip if agent is unhealthy ---
        try:
            from app.healing.circuit_breaker import get_circuit_breaker
            cb = get_circuit_breaker()
            if not await cb.is_available(self.name):
                logger.warning("Agent '%s' circuit open — returning degraded result", self.name)
                return AgentResult(
                    output={"error": f"Agent {self.name} temporarily unavailable (circuit open)", "_degraded": True},
                    provider="local", model="circuit-breaker",
                )
        except Exception:
            pass  # circuit breaker is optional

        # --- recall: fetch relevant context before execution (fast timeout) ---
        memory_context: dict = {}
        try:
            query = str(input_data.get("text", input_data.get("task", "")))[:500]
            memory_context = await asyncio.wait_for(
                self._memory.recall(agent_id=self.name, query=query),
                timeout=_MEMORY_TIMEOUT,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.debug("Memory recall skipped for '%s': %s", self.name, type(exc).__name__)

        # Inject context so subclasses can optionally use it
        enriched_input = {**input_data, "_memory_context": memory_context}

        # --- execute: delegate to subclass ---
        from app.memory.experience import ExperienceCollector
        collector = ExperienceCollector(self.name, self.agent_type)
        try:
            result = await self.execute(enriched_input, config)
        except Exception as exc:
            await asyncio.wait_for(collector.collect_error(exc, input_data), timeout=_MEMORY_TIMEOUT)
            raise

        # --- record health: track success in circuit breaker ---
        try:
            from app.healing.circuit_breaker import get_circuit_breaker
            cb = get_circuit_breaker()
            is_fallback = result.provider == "local" and result.model in ("fallback", "circuit-breaker")
            if not is_fallback:
                await cb.record_success(self.name)
        except Exception:
            pass

        # --- remember: persist structured experience (replaces plain text summary) ---
        try:
            await asyncio.wait_for(
                collector.collect_success(result, input_data),
                timeout=_MEMORY_TIMEOUT,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.debug("Memory remember skipped for '%s': %s", self.name, type(exc).__name__)

        return result

    @abstractmethod
    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        """Execute the agent's task. Override in subclasses."""
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10, jitter=2),
        retry=retry_if_exception(_should_retry),
        reraise=True,
    )
    async def _resilient_llm_call(self, messages: list[dict], **kwargs):
        """LLM call with automatic retry on transient failures.

        Passes agent name to router so it can select the correct local model.
        Fallback chain: Ollama (local) → Groq (free cloud) → Claude (paid cloud).
        """
        from app.llm.router import get_router
        router = get_router()
        return await router.chat(messages, agent_name=self.name, **kwargs)

    @staticmethod
    def _extract_text(input_data: dict) -> str:
        """Extract usable text from input_data, checking multiple common keys.
        Agents use different key names — this ensures we find content regardless."""
        for key in ("text", "task", "question", "topic", "description", "data", "content", "input"):
            val = input_data.get(key, "")
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        # Check dependency outputs from previous steps
        for key, val in input_data.items():
            if key.startswith("_") and key.endswith("_output") and isinstance(val, dict):
                # Extract text from previous step's output
                for sub_key in ("summary", "extracted_text", "answer", "report_markdown", "translated_text"):
                    sub_val = val.get(sub_key, "")
                    if sub_val and isinstance(sub_val, str) and sub_val.strip():
                        return sub_val.strip()[:3000]
        # Last resort: serialize the whole input as text
        import json
        raw = json.dumps({k: v for k, v in input_data.items() if not k.startswith("_")}, default=str)
        return raw[:3000] if len(raw) > 10 else ""

    def _build_system_prompt(self, task_description: str) -> str:
        return (
            f"You are {self.name}, a specialized AI agent. "
            f"Your role: {self.description}\n\n"
            f"Task: {task_description}"
        )

    def _build_system_prompt_v2(self, task_description: str) -> str:
        """Phase 5a — Agent Skills-aware system prompt builder.

        Attempts to load a skill file at
        ``backend/skills/<self.agent_type>/SKILL.md`` and, if present,
        uses its body as the core of the system prompt. If no skill is
        found, or if skill loading fails for any reason (parse error,
        disk read error, missing file), the method falls back to the
        legacy ``_build_system_prompt`` output **byte-for-byte** so
        callers can opt into this method without risk of drift.

        Per the project rule "NEVER modify existing encapsulated
        components", ``_build_system_prompt`` is left untouched.
        Subclasses that want to use Agent Skills must explicitly call
        ``_build_system_prompt_v2`` in their ``execute`` method.

        Environment overrides:
            NEXUSFORGE_SKILLS_DISABLED=1 — bypass skill loading
            entirely and behave identically to
            ``_build_system_prompt``. Useful for an emergency
            rollback without redeploying.
        """
        import os as _os
        if _os.environ.get("NEXUSFORGE_SKILLS_DISABLED", "0") == "1":
            return self._build_system_prompt(task_description)

        try:
            from app.agents.skill_loader import get_default_loader
            loader = get_default_loader()
            skill = loader.load(self.agent_type)
        except Exception as exc:
            logger.debug("Skill loader error for %s: %s", self.agent_type, exc)
            skill = None

        if skill is None:
            return self._build_system_prompt(task_description)

        # Skill found — use the body as the role definition. We
        # keep the "You are {name}" identity prefix so the agent's
        # self-reference stays consistent with the legacy path, and
        # we append the task_description at the end in the same
        # position as the legacy method.
        return (
            f"You are {self.name}, a specialized AI agent.\n\n"
            f"{skill.body}\n\n"
            f"Task: {task_description}"
        )
