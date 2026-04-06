"""ExperienceCollector — auto-documents every agent execution as structured experience.

Hooks into BaseAgent.run() to capture:
  - which model was used (local vs cloud)
  - cost, tokens, duration
  - tools used (capabilities)
  - success/fallback/error outcome
  - input summary + output summary

This feeds each agent's memory so they accumulate real experience over time.
The orchestrator can read this via OrchestratorMemory.get_experience_feed().
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRecord:
    """Structured record of a single agent execution."""
    agent_name: str
    agent_type: str
    input_summary: str
    output_summary: str
    provider: str
    model: str
    tokens_used: int
    cost_usd: float
    duration_sec: float
    outcome: str          # "success" | "fallback" | "error"
    tools_used: list[str] = field(default_factory=list)
    error: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_memory_text(self) -> str:
        """Convert to natural language for LLM context injection."""
        lines = [
            f"Agent {self.agent_name} executed at {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.timestamp))}.",
            f"Input: {self.input_summary[:200]}",
            f"Output: {self.output_summary[:300]}",
            f"Model: {self.model} via {self.provider} | {self.tokens_used} tokens | ${self.cost_usd:.4f} | {self.duration_sec:.1f}s",
            f"Outcome: {self.outcome}",
        ]
        if self.tools_used:
            lines.append(f"Tools used: {', '.join(self.tools_used)}")
        if self.error:
            lines.append(f"Error: {self.error}")
        return "\n".join(lines)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "type": "execution",
            "agent": self.agent_name,
            "agent_type": self.agent_type,
            "provider": self.provider,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "duration_sec": self.duration_sec,
            "outcome": self.outcome,
            "tools_used": self.tools_used,
            "timestamp": self.timestamp,
        }


class ExperienceCollector:
    """Wraps an agent execution and persists a structured experience record.

    Usage inside BaseAgent.run():
        async with ExperienceCollector(agent) as collector:
            result = await self.execute(input_data, config)
            collector.set_result(result, input_data)
    """

    def __init__(self, agent_name: str, agent_type: str):
        self.agent_name = agent_name
        self.agent_type = agent_type
        self._start = time.monotonic()
        self._memory = MemoryManager()
        self._tools_used: list[str] = []
        self._result = None
        self._input_data: dict = {}

    def record_tool(self, tool_name: str):
        """Call this when a capability/tool is used."""
        self._tools_used.append(tool_name)

    def set_result(self, result, input_data: dict):
        self._result = result
        self._input_data = input_data

    async def _persist(self, outcome: str, error: str | None = None):
        if self._result is None and error is None:
            return

        duration = time.monotonic() - self._start
        input_text = str(self._input_data)[:300]

        if self._result:
            output_text = str(self._result.output)[:400]
            provider = self._result.provider
            model = self._result.model
            tokens = self._result.tokens_used
            cost = self._result.cost_usd
        else:
            output_text = f"ERROR: {error}"
            provider = "none"
            model = "none"
            tokens = 0
            cost = 0.0

        record = ExecutionRecord(
            agent_name=self.agent_name,
            agent_type=self.agent_type,
            input_summary=input_text,
            output_summary=output_text,
            provider=provider,
            model=model,
            tokens_used=tokens,
            cost_usd=cost,
            duration_sec=round(duration, 2),
            outcome=outcome,
            tools_used=self._tools_used,
            error=error,
        )

        try:
            await self._memory.remember(
                agent_id=self.agent_name,
                text=record.to_memory_text(),
                tier="episodic",
                metadata=record.to_metadata(),
            )
            logger.debug(
                "ExperienceCollector: saved %s execution (%s, %.1fs, %s)",
                self.agent_name, outcome, duration, provider,
            )
        except Exception as exc:
            logger.warning("ExperienceCollector failed to persist: %s", exc)

    async def collect_success(self, result, input_data: dict):
        self.set_result(result, input_data)
        is_fallback = result.provider in ("local",) and result.model in ("fallback", "circuit-breaker")
        outcome = "fallback" if is_fallback else "success"
        await self._persist(outcome)

    async def collect_error(self, error: Exception, input_data: dict):
        self._input_data = input_data
        await self._persist("error", error=str(error)[:200])
