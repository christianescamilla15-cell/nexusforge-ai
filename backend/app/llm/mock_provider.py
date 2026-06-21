"""Mock LLM provider — deterministic, zero-cost, zero-dependency fallback.

Ported from CallForge's `infrastructure/llm/mock_provider.py` (cross-pollination
graft, 2026-06-21). Adds a final fallback option to the LLMRouter so the system
never crashes due to LLM unavailability and can demo without any API keys or
local Ollama running.

Usage: enable via `settings.mock_llm_enabled = True` (default OFF in prod).
When enabled, MockProvider is appended as the last link in the fallback chain
in `app.llm.router.LLMRouter._build_provider_chain`.
"""

from __future__ import annotations

import hashlib
import json

from app.config import settings
from app.llm.provider import BaseLLMProvider, LLMResponse


_DEFAULT_REPLY = (
    "Mock LLM response (no live provider configured). "
    "Set GROQ_API_KEY, enable Ollama, or configure Claude to get real answers."
)


class MockProvider(BaseLLMProvider):
    """Deterministic stub: returns a stable response derived from the input hash.

    Why deterministic: the workflow can still be exercised end-to-end (tests,
    smoke checks, recruiter demos) without paying or running anything else.
    Hashing the input ensures replay-stable behavior so snapshot tests work.
    """

    name = "mock"

    def __init__(self) -> None:
        self._enabled = bool(getattr(settings, "mock_llm_enabled", False))

    def is_available(self) -> bool:
        return self._enabled

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        context_management: dict | None = None,
    ) -> LLMResponse:
        del temperature, max_tokens, context_management  # ignored on purpose

        # Hash the conversation so repeat calls return the same answer.
        canonical = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:8]

        # If the last user message looks like a request for JSON, emit a tiny
        # JSON envelope so downstream JSON-parsing agents (Extractor, Validator,
        # etc.) don't crash on the mock path.
        last = messages[-1].get("content", "") if messages else ""
        wants_json = (
            "json" in last.lower()
            or last.strip().startswith("{")
            or "schema" in last.lower()
        )
        if wants_json:
            text = json.dumps(
                {"mock": True, "echo_hash": digest, "note": _DEFAULT_REPLY}
            )
        else:
            text = f"{_DEFAULT_REPLY} [trace={digest}]"

        return LLMResponse(
            text=text,
            tokens_input=sum(len(m.get("content", "")) // 4 for m in messages),
            tokens_output=len(text) // 4,
            model="mock-deterministic",
            provider=self.name,
            cost_usd=0.0,
            thinking="",
        )
