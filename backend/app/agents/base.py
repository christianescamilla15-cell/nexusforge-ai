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
    # Last resort: raise with context
    raise json.JSONDecodeError(f"Cannot parse LLM response as JSON: {t[:200]}", t, 0)


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
        self._memory = MemoryManager()

    async def run(self, input_data: dict, config: dict = None) -> AgentResult:
        """Public entrypoint: circuit breaker check → recall → execute → remember."""
        config = config or {}

        # --- circuit breaker: skip if agent is unhealthy ---
        try:
            from app.healing.circuit_breaker import get_circuit_breaker
            cb = get_circuit_breaker()
            if not cb.is_available(self.name):
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
        result = await self.execute(enriched_input, config)

        # --- record health: track success in circuit breaker ---
        try:
            from app.healing.circuit_breaker import get_circuit_breaker
            cb = get_circuit_breaker()
            is_fallback = result.provider == "local" and result.model in ("fallback", "circuit-breaker")
            if not is_fallback:
                cb.record_success(self.name)
        except Exception:
            pass

        # --- remember: persist result after execution (fast timeout) ---
        try:
            summary = str(result.output)[:1000]
            is_fallback = result.provider == "local" and result.model in ("fallback", "circuit-breaker")
            await asyncio.wait_for(
                self._memory.remember(
                    agent_id=self.name,
                    text=summary,
                    tier="episodic",
                    metadata={
                        "type": "execution",
                        "agent": self.name,
                        "tokens_used": result.tokens_used,
                        "cost_usd": result.cost_usd,
                        "outcome": "fallback" if is_fallback else "success",
                    },
                ),
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

        Retries up to 3 times with exponential backoff + jitter.
        Retries ALL exceptions except programming errors (ValueError, TypeError, etc.).
        """
        from app.llm.router import get_router
        router = get_router()
        return await router.chat(messages, **kwargs)

    def _build_system_prompt(self, task_description: str) -> str:
        return (
            f"You are {self.name}, a specialized AI agent. "
            f"Your role: {self.description}\n\n"
            f"Task: {task_description}"
        )
