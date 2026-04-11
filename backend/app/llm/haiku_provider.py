"""Haiku LLM provider — fast, cheap classification and routing.

Claude Haiku 4.5: $1/MTok input, $5/MTok output
5x cheaper than Sonnet, ideal for:
- Intent classification
- Agent routing decisions
- Quick validation
- Simple transformations
"""

import httpx
import anthropic
from app.config import settings
from app.llm.provider import BaseLLMProvider, LLMResponse

HAIKU_MODEL = "claude-haiku-4-5-20251001"


class HaikuProvider(BaseLLMProvider):
    name = "haiku"

    def __init__(self):
        self._api_key = settings.anthropic_api_key
        self._client: anthropic.AsyncAnthropic | None = None

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def chat(self, messages: list[dict], temperature: float = 0.1,
                   max_tokens: int = 512,
                   context_management: dict | None = None) -> LLMResponse:
        client = self._get_client()

        system_text = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": HAIKU_MODEL,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_messages,
        }
        if system_text:
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        # Context Editing (Feature 1) — beta path only when the caller opts in.
        # See claude_provider.py for the full explanation of why the two branches
        # are kept separate.
        if context_management is not None:
            kwargs["context_management"] = context_management
            response = await client.beta.messages.create(
                **kwargs,
                betas=["context-management-2025-06-27"],
                timeout=httpx.Timeout(30.0),
            )
        else:
            response = await client.messages.create(**kwargs, timeout=httpx.Timeout(30.0))

        text = response.content[0].text if response.content else ""
        usage = response.usage
        cost = (usage.input_tokens / 1_000_000) * 1.0 + (usage.output_tokens / 1_000_000) * 5.0

        return LLMResponse(
            text=text,
            tokens_input=usage.input_tokens,
            tokens_output=usage.output_tokens,
            model=response.model,
            provider="haiku",
            cost_usd=round(cost, 6),
        )
