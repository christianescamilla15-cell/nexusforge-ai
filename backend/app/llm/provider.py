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
    cost_usd: float = 0.0
    thinking: str = ""


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    name: str = "unknown"

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.3,
                   max_tokens: int = 2048,
                   context_management: dict | None = None) -> LLMResponse:
        """Send messages and get a completion response.

        context_management: optional dict passed to Anthropic's beta
            context editing API (beta header context-management-2025-06-27).
            Shape: {"edits": [{"type": "clear_tool_uses_20250919", ...}, ...]}.
            Providers that do not implement beta context editing (Ollama, Groq)
            silently ignore this parameter. Only ClaudeProvider and HaikuProvider
            actually consume it today.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider has credentials configured."""
        pass
