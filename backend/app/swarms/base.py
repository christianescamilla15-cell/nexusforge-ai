"""Base swarm class — all topologies inherit from this."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SwarmResult:
    """Unified result from any swarm execution."""
    output: dict
    topology: str
    agents_used: list[str] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    steps_executed: int = 0
    duration_ms: int = 0


class BaseSwarm(ABC):
    """Abstract base for all swarm topologies."""

    name: str = "unnamed"
    topology: str = "unknown"

    @abstractmethod
    async def execute(
        self,
        input_data: dict,
        agent_types: list[str],
        config: dict = None,
    ) -> SwarmResult:
        """Execute the swarm with given agents and input."""
        pass
