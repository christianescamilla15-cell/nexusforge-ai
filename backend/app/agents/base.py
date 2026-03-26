"""Abstract base agent class for all NexusForge agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AgentResult:
    """Unified result from any agent execution."""
    output: dict
    tokens_used: int = 0
    cost_usd: float = 0.0
    provider: str = "local"
    model: str = "none"


class BaseAgent(ABC):
    """Base class all agents must inherit from."""

    name: str = "unnamed"
    agent_type: str = "unknown"
    description: str = ""

    @abstractmethod
    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        """Execute the agent's task and return a result."""
        pass

    def _build_system_prompt(self, task_description: str) -> str:
        return (
            f"You are {self.name}, a specialized AI agent. "
            f"Your role: {self.description}\n\n"
            f"Task: {task_description}"
        )
