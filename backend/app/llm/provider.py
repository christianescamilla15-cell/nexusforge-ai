"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""
    text: str
    tokens_input: int
    tokens_output: int
    model: str
    provider: str


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    name: str = "unknown"

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.3,
                   max_tokens: int = 2048) -> LLMResponse:
        """Send messages and get a completion response."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider has credentials configured."""
        pass
