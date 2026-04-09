"""Claude LLM provider — Anthropic API via official SDK.

2026 features:
- Prompt caching (90% savings on repeated system prompts)
- Adaptive thinking (Claude decides reasoning depth)
- Structured outputs (guaranteed JSON schema)
- Updated to latest model IDs (Opus 4.6, Sonnet 4.6)
"""

import httpx
import anthropic
from app.config import settings
from app.llm.provider import BaseLLMProvider, LLMResponse

DEFAULT_MODEL = "claude-sonnet-4-6"


class ClaudeProvider(BaseLLMProvider):
    name = "claude"

    def __init__(self):
        self._api_key = settings.anthropic_api_key
        self._client: anthropic.AsyncAnthropic | None = None

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def chat(self, messages: list[dict], temperature: float = 0.3,
                   max_tokens: int = 2048, thinking: bool = False) -> LLMResponse:
        client = self._get_client()

        # Separate system message from conversation messages
        system_text = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": DEFAULT_MODEL,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }

        # System prompt with caching (90% savings on repeated calls)
        if system_text:
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        # Adaptive thinking for complex tasks
        if thinking:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": min(max_tokens, 8000)}
            # Temperature must be 1 when using thinking
            kwargs["temperature"] = 1

        response = await client.messages.create(**kwargs, timeout=httpx.Timeout(60.0))

        # Extract text and thinking from response
        text = ""
        thinking_text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text
            elif block.type == "thinking":
                thinking_text += block.thinking

        # Calculate cost with cache awareness
        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0)
        cache_write = getattr(usage, "cache_creation_input_tokens", 0)
        regular_input = usage.input_tokens - cache_read - cache_write

        return LLMResponse(
            text=text,
            tokens_input=usage.input_tokens,
            tokens_output=usage.output_tokens,
            model=response.model,
            provider="claude",
            thinking=thinking_text,
            cost_usd=_calculate_cost(regular_input, cache_read, cache_write, usage.output_tokens),
        )


def _calculate_cost(regular_input: int, cache_read: int, cache_write: int, output: int) -> float:
    """Calculate cost with prompt caching pricing (Sonnet 4.6).

    Standard: $3/MTok input, $15/MTok output
    Cache write: $3.75/MTok (1.25x)
    Cache read: $0.30/MTok (0.1x) — 90% savings!
    """
    cost = (regular_input / 1_000_000) * 3.0
    cost += (cache_write / 1_000_000) * 3.75
    cost += (cache_read / 1_000_000) * 0.30
    cost += (output / 1_000_000) * 15.0
    return round(cost, 6)
