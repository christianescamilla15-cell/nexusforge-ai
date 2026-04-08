"""Ollama local LLM provider — OpenAI-compatible API + native thinking mode."""

import httpx
from app.config import settings
from app.llm.provider import BaseLLMProvider, LLMResponse

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
DEFAULT_MODEL = "qwen2.5-coder:7b"

# Models that support native thinking via Ollama's /api/chat endpoint
THINKING_MODELS = {"gemma4:27b", "deepseek-r1:8b"}


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
        """Route to thinking or standard chat based on model."""
        if self._model in THINKING_MODELS:
            return await self._chat_with_thinking(messages, temperature, max_tokens)
        return await self._chat_standard(messages, temperature, max_tokens)

    async def _chat_standard(self, messages: list[dict], temperature: float,
                             max_tokens: int) -> LLMResponse:
        """Standard OpenAI-compatible chat completion."""
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

    async def _chat_with_thinking(self, messages: list[dict], temperature: float,
                                  max_tokens: int) -> LLMResponse:
        """Native Ollama chat API with thinking mode enabled.

        Uses /api/chat (not OpenAI-compatible) to get the thinking field
        that models like gemma4:27b and deepseek-r1:8b produce.
        """
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "think": True,
        }

        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        msg = data.get("message", {})
        text = msg.get("content", "")
        thinking = msg.get("thinking", "")

        # Token counts from Ollama native API
        tokens_in = data.get("prompt_eval_count", 0)
        tokens_out = data.get("eval_count", 0)

        return LLMResponse(
            text=text,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            model=self._model,
            provider="ollama",
            thinking=thinking,
        )
