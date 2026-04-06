"""LocalModelClient — direct Ollama connection per agent.

Each agent gets its own dedicated local model instance.
Falls back to the global router (Groq → Claude) if Ollama is unavailable.

Usage in an agent:
    from app.llm.local_client import LocalModelClient

    class RepairAgent(BaseAgent):
        _local = LocalModelClient("qwen2.5-coder:7b")

        async def execute(self, input_data, config=None):
            response = await self._local.chat(messages)
            # if Ollama is down → automatically falls back to router
"""

import logging
import httpx
from app.llm.provider import LLMResponse

logger = logging.getLogger(__name__)

OLLAMA_BASE = "http://localhost:11434"


class LocalModelClient:
    """Dedicated local LLM client bound to a specific Ollama model.

    Tries Ollama first. On failure, falls back to the global router
    (Groq → Claude) transparently — no code change needed in the agent.
    """

    def __init__(self, model: str):
        self.model = model
        self._available: bool | None = None  # None = not checked yet

    async def _check_available(self) -> bool:
        """Ping Ollama to confirm it's running."""
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"{OLLAMA_BASE}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        agent_name: str = "",
    ) -> LLMResponse:
        """Send chat request. Uses local model when available, router as fallback."""

        # Check Ollama availability (lazy, cached per request)
        if await self._check_available():
            try:
                return await self._call_ollama(messages, temperature, max_tokens)
            except Exception as exc:
                logger.warning(
                    "Local model %s failed (%s) — falling back to router", self.model, exc
                )

        # Fallback: global router (Groq → Claude)
        from app.llm.router import get_router
        router = get_router()
        return await router.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            agent_name=agent_name,
        )

    async def _call_ollama(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OLLAMA_BASE}/v1/chat/completions", json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            text=choice,
            tokens_input=usage.get("prompt_tokens", 0),
            tokens_output=usage.get("completion_tokens", 0),
            model=self.model,
            provider="ollama",
        )

    @property
    def cost_usd(self) -> float:
        return 0.0  # local inference is always free
