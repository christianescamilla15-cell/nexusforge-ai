"""Abstract base agent class for all NexusForge agents."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Fast timeout for memory ops — don't let broken Redis block execution
_MEMORY_TIMEOUT = 2  # seconds


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
        """Public entrypoint: recall → execute → remember."""
        config = config or {}

        # --- recall: fetch relevant context before execution (fast timeout) ---
        memory_context: dict = {}
        try:
            query = str(input_data)[:500]
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

        # --- remember: persist result after execution (fast timeout) ---
        try:
            summary = str(result.output)[:1000]
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
                        "outcome": "success",
                    },
                ),
                timeout=_MEMORY_TIMEOUT,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.debug("Memory remember skipped for '%s': %s", self.name, type(exc).__name__)

        return result

    @abstractmethod
    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        """Execute the agent's task. Override in subclasses.

        ``input_data`` will contain a ``_memory_context`` key with recalled
        memories when called via ``run()``.
        """
        pass

    def _build_system_prompt(self, task_description: str) -> str:
        return (
            f"You are {self.name}, a specialized AI agent. "
            f"Your role: {self.description}\n\n"
            f"Task: {task_description}"
        )
