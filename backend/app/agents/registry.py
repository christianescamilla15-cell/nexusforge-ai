"""Agent registry — maps agent_type strings to agent instances."""

from typing import Protocol

from app.agents.base import AgentResult  # canonical AgentResult with provider/model


class AgentProtocol(Protocol):
    async def execute(self, input_data: dict, config: dict) -> AgentResult:
        ...


_registry: dict[str, AgentProtocol] = {}


def register_agent(agent_type: str, agent: AgentProtocol):
    _registry[agent_type] = agent


def get_agent(agent_type: str) -> AgentProtocol:
    if agent_type not in _registry:
        raise ValueError(f"Unknown agent type: '{agent_type}'. Registered: {list(_registry.keys())}")
    return _registry[agent_type]


def list_agents() -> list[str]:
    return list(_registry.keys())
