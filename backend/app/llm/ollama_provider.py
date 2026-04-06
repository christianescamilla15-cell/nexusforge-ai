"""Ollama local LLM provider — OpenAI-compatible API."""

import httpx
from app.config import settings
from app.llm.provider import BaseLLMProvider, LLMResponse

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
DEFAULT_MODEL = "qwen2.5-coder:7b"


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self):
        self._base_url = getattr(settings, "ollama_url", "http://localhost:11434")
        self._model = getattr(settings, "ollama_model", DEFAULT_MODEL)
        self._enabled = getattr(settings, "ollama_enabled", False)

    def is_available(self) -> bool:
        return bool(self._enabled)

    def set_model(self, model: str) -> None:
        """Override model for this request (called by router per agent)."""
        self._model = model

    async def chat(self, messages: list[dict], temperature: float = 0.3,
                   max_tokens: int = 2048) -> LLMResponse:
        url = f"{self._base_url}/v1/chat/completions"
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            text=choice,
            tokens_input=usage.get("prompt_tokens", 0),
            tokens_output=usage.get("completion_tokens", 0),
            model=self._model,
            provider="ollama",
        )
