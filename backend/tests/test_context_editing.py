"""Tests for Feature 1 — Context Editing (Anthropic beta context-management-2025-06-27).

Verifies the provider layer routes calls to the correct Anthropic endpoint
depending on whether a caller opted in to beta context editing:

- context_management=None  → client.messages.create (existing path, unchanged)
- context_management=dict  → client.beta.messages.create with betas=[...] header

The goal is to prove the plumbing is correct without making real network
calls. The anthropic client is fully mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.claude_provider import ClaudeProvider
from app.llm.haiku_provider import HaikuProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.groq_provider import GroqProvider


# ---------- Shared mock fixture ----------

def _fake_anthropic_response(input_tokens: int = 100, output_tokens: int = 20):
    """Build a minimal mock Anthropic Message response that the providers expect.

    Must expose: content (list of blocks with .type/.text/.thinking),
    usage (input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens),
    model (str).
    """
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "ok"

    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_input_tokens = 0
    usage.cache_creation_input_tokens = 0

    response = MagicMock()
    response.content = [text_block]
    response.usage = usage
    response.model = "claude-test"
    return response


# ---------- Claude provider ----------

@pytest.mark.asyncio
async def test_claude_provider_without_context_management_uses_legacy_path():
    """When context_management is None, ClaudeProvider must use client.messages.create
    (not client.beta.messages.create). Ensures zero behavioral change for existing
    call sites."""
    provider = ClaudeProvider()
    provider._api_key = "sk-test-dummy"  # force is_available()

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=_fake_anthropic_response())
    fake_client.beta.messages.create = AsyncMock(return_value=_fake_anthropic_response())

    with patch.object(provider, "_get_client", return_value=fake_client):
        resp = await provider.chat(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.3,
            max_tokens=128,
            # context_management omitted
        )

    assert fake_client.messages.create.await_count == 1, "legacy path must be used"
    assert fake_client.beta.messages.create.await_count == 0, "beta path must NOT be used"
    assert resp.provider == "claude"


@pytest.mark.asyncio
async def test_claude_provider_with_context_management_uses_beta_path():
    """When context_management is set, ClaudeProvider must route through the beta
    endpoint and pass the required beta header."""
    provider = ClaudeProvider()
    provider._api_key = "sk-test-dummy"

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=_fake_anthropic_response())
    fake_client.beta.messages.create = AsyncMock(return_value=_fake_anthropic_response())

    ctx_mgmt = {
        "edits": [
            {
                "type": "clear_tool_uses_20250919",
                "trigger": {"type": "input_tokens", "value": 35000},
                "keep": {"type": "tool_uses", "value": 5},
                "clear_at_least": {"type": "input_tokens", "value": 2000},
            }
        ]
    }

    with patch.object(provider, "_get_client", return_value=fake_client):
        await provider.chat(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.3,
            max_tokens=128,
            context_management=ctx_mgmt,
        )

    assert fake_client.messages.create.await_count == 0, "legacy path must NOT be used"
    assert fake_client.beta.messages.create.await_count == 1, "beta path must be used"

    # Verify the beta header and context_management payload were passed correctly
    call_kwargs = fake_client.beta.messages.create.await_args.kwargs
    assert call_kwargs["betas"] == ["context-management-2025-06-27"]
    assert call_kwargs["context_management"] == ctx_mgmt


# ---------- Haiku provider ----------

@pytest.mark.asyncio
async def test_haiku_provider_without_context_management_uses_legacy_path():
    provider = HaikuProvider()
    provider._api_key = "sk-test-dummy"

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=_fake_anthropic_response())
    fake_client.beta.messages.create = AsyncMock(return_value=_fake_anthropic_response())

    with patch.object(provider, "_get_client", return_value=fake_client):
        await provider.chat(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.1,
            max_tokens=64,
        )

    assert fake_client.messages.create.await_count == 1
    assert fake_client.beta.messages.create.await_count == 0


@pytest.mark.asyncio
async def test_haiku_provider_with_context_management_uses_beta_path():
    provider = HaikuProvider()
    provider._api_key = "sk-test-dummy"

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=_fake_anthropic_response())
    fake_client.beta.messages.create = AsyncMock(return_value=_fake_anthropic_response())

    ctx_mgmt = {"edits": [{"type": "clear_tool_uses_20250919"}]}

    with patch.object(provider, "_get_client", return_value=fake_client):
        await provider.chat(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.1,
            max_tokens=64,
            context_management=ctx_mgmt,
        )

    assert fake_client.messages.create.await_count == 0
    assert fake_client.beta.messages.create.await_count == 1
    call_kwargs = fake_client.beta.messages.create.await_args.kwargs
    assert call_kwargs["betas"] == ["context-management-2025-06-27"]
    assert call_kwargs["context_management"] == ctx_mgmt


# ---------- Ollama and Groq: silent drop ----------

@pytest.mark.asyncio
async def test_ollama_provider_accepts_and_drops_context_management():
    """OllamaProvider.chat must accept context_management in its signature
    without raising, since the router passes it uniformly to all providers.
    Ollama has no equivalent feature, so the kwarg is silently dropped."""
    provider = OllamaProvider()
    provider._enabled = False  # skip real HTTP

    # Just verify the signature accepts the kwarg. We don't actually call
    # the HTTP path because provider is disabled — the point is that
    # the TypeError "got unexpected keyword argument" would fire before
    # is_available() matters, during parameter binding.
    import inspect
    sig = inspect.signature(provider.chat)
    assert "context_management" in sig.parameters
    assert sig.parameters["context_management"].default is None


@pytest.mark.asyncio
async def test_groq_provider_accepts_and_drops_context_management():
    provider = GroqProvider()
    import inspect
    sig = inspect.signature(provider.chat)
    assert "context_management" in sig.parameters
    assert sig.parameters["context_management"].default is None


# ---------- Base provider contract ----------

def test_base_provider_signature_includes_context_management():
    """The abstract BaseLLMProvider.chat signature must list context_management
    so that implementing classes know they must accept it (even if they drop it)."""
    from app.llm.provider import BaseLLMProvider
    import inspect
    sig = inspect.signature(BaseLLMProvider.chat)
    assert "context_management" in sig.parameters
    assert sig.parameters["context_management"].default is None


# ---------- Router propagation ----------

@pytest.mark.asyncio
async def test_router_propagates_context_management_to_provider():
    """LLMRouter.chat must forward context_management to the selected provider."""
    from app.llm.router import LLMRouter

    router = LLMRouter()

    # Replace all providers with mocks so the chain is deterministic
    fake_resp = MagicMock()
    fake_resp.text = "ok"
    fake_resp.tokens_input = 10
    fake_resp.tokens_output = 5
    fake_resp.model = "test"
    fake_resp.provider = "mock"
    fake_resp.cost_usd = 0.0

    mock_claude = MagicMock()
    mock_claude.name = "claude"
    mock_claude.is_available = MagicMock(return_value=True)
    mock_claude.chat = AsyncMock(return_value=fake_resp)

    router._claude = mock_claude
    # Also make the others unavailable so we don't fall through unexpectedly
    router._ollama.is_available = MagicMock(return_value=False)
    router._groq.is_available = MagicMock(return_value=False)
    router._haiku.is_available = MagicMock(return_value=False)

    ctx_mgmt = {"edits": [{"type": "clear_tool_uses_20250919"}]}

    # ComplianceAgent is the only _CLAUDE_ONLY_AGENT, so it maps to
    # provider_chain = [self._claude]
    await router.chat(
        messages=[{"role": "user", "content": "hi"}],
        agent_name="ComplianceAgent",
        context_management=ctx_mgmt,
    )

    mock_claude.chat.assert_awaited_once()
    call_kwargs = mock_claude.chat.await_args.kwargs
    assert call_kwargs["context_management"] == ctx_mgmt


@pytest.mark.asyncio
async def test_router_passes_none_when_context_management_not_specified():
    """Default behavior: router passes context_management=None to the provider."""
    from app.llm.router import LLMRouter

    router = LLMRouter()

    fake_resp = MagicMock()
    fake_resp.text = "ok"
    fake_resp.tokens_input = 10
    fake_resp.tokens_output = 5
    fake_resp.model = "test"
    fake_resp.provider = "mock"
    fake_resp.cost_usd = 0.0

    mock_claude = MagicMock()
    mock_claude.name = "claude"
    mock_claude.is_available = MagicMock(return_value=True)
    mock_claude.chat = AsyncMock(return_value=fake_resp)

    router._claude = mock_claude
    router._ollama.is_available = MagicMock(return_value=False)
    router._groq.is_available = MagicMock(return_value=False)
    router._haiku.is_available = MagicMock(return_value=False)

    await router.chat(
        messages=[{"role": "user", "content": "hi"}],
        agent_name="ComplianceAgent",
    )

    mock_claude.chat.assert_awaited_once()
    call_kwargs = mock_claude.chat.await_args.kwargs
    assert call_kwargs["context_management"] is None
