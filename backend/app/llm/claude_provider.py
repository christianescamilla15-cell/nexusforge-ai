"""Claude LLM provider — Anthropic API via official SDK."""

import anthropic
from app.config import settings
from app.llm.provider import BaseLLMProvider, LLMResponse

DEFAULT_MODEL = "claude-sonnet-4-20250514"


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
                   max_tokens: int = 2048) -> LLMResponse:
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
        if system_text:
            kwargs["system"] = system_text

        response = await client.messages.create(**kwargs)

        text = response.content[0].text if response.content else ""
        return LLMResponse(
            text=text,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            model=response.model,
            provider="claude",
        )
