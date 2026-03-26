"""Groq LLM provider — Llama 3.3 70B via Groq cloud API."""

import httpx
from app.config import settings
from app.llm.provider import BaseLLMProvider, LLMResponse

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class GroqProvider(BaseLLMProvider):
    name = "groq"

    def __init__(self):
        self._api_key = settings.groq_api_key

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def chat(self, messages: list[dict], temperature: float = 0.3,
                   max_tokens: int = 2048) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": DEFAULT_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(GROQ_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            text=choice,
            tokens_input=usage.get("prompt_tokens", 0),
            tokens_output=usage.get("completion_tokens", 0),
            model=data.get("model", DEFAULT_MODEL),
            provider="groq",
        )
