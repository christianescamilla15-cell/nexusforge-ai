"""User LLM provider — routes through user's own API keys.

Supports: Groq, Claude, OpenAI (GPT-4o), OpenAI (GPT-4o-mini)
Users store their keys in nf_user_keys table and select provider per workflow.
"""

import logging
from typing import Optional

from app.llm.provider import LLMResponse
from app.llm.groq_provider import GroqProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.token_tracker import calculate_cost

logger = logging.getLogger(__name__)


async def route_with_user_key(
    provider: str,
    api_key: str,
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
    model: Optional[str] = None,
) -> LLMResponse:
    """Route LLM call through a user-provided API key.

    Args:
        provider: 'groq', 'claude', 'openai', 'openai-gpt4o'
        api_key: User's API key for that provider
        messages: Chat messages
        temperature: LLM temperature
        max_tokens: Max output tokens
        model: Override model (optional)

    Returns:
        LLMResponse with text, tokens, cost
    """
    if provider == "groq":
        p = GroqProvider()
        p._api_key = api_key
        response = await p.chat(messages, temperature, max_tokens)

    elif provider == "claude":
        p = ClaudeProvider()
        p._api_key = api_key
        response = await p.chat(messages, temperature, max_tokens)

    elif provider in ("openai", "openai-gpt4o-mini"):
        p = OpenAIProvider(api_key=api_key, model=model or "gpt-4o-mini")
        response = await p.chat(messages, temperature, max_tokens)

    elif provider == "openai-gpt4o":
        p = OpenAIProvider(api_key=api_key, model=model or "gpt-4o")
        response = await p.chat(messages, temperature, max_tokens)

    else:
        raise ValueError(f"Unknown provider: {provider}. Supported: groq, claude, openai, openai-gpt4o")

    # Calculate cost
    response.cost_usd = calculate_cost(response.provider, response.tokens_input, response.tokens_output)
    return response


# Available providers for the UI
AVAILABLE_PROVIDERS = [
    {
        "id": "groq",
        "name": "Groq (Llama 3.3 70B)",
        "models": ["llama-3.3-70b-versatile"],
        "pricing": {"input": 0.59, "output": 0.79},
        "speed": "fast",
        "key_placeholder": "gsk_...",
    },
    {
        "id": "claude",
        "name": "Anthropic Claude",
        "models": ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"],
        "pricing": {"input": 3.00, "output": 15.00},
        "speed": "medium",
        "key_placeholder": "sk-ant-...",
    },
    {
        "id": "openai-gpt4o",
        "name": "OpenAI GPT-4o",
        "models": ["gpt-4o"],
        "pricing": {"input": 2.50, "output": 10.00},
        "speed": "medium",
        "key_placeholder": "sk-...",
    },
    {
        "id": "openai",
        "name": "OpenAI GPT-4o Mini",
        "models": ["gpt-4o-mini"],
        "pricing": {"input": 0.15, "output": 0.60},
        "speed": "fast",
        "key_placeholder": "sk-...",
    },
]
