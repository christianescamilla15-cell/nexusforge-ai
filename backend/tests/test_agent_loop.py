"""Tests for agent_loop.run_memory_loop — Phase 3.

Exercises the multi-turn tool-use loop using mocked Anthropic clients.
The tests cover:

- Single-turn path: no tool uses, final text returned immediately
- Multi-turn path: one tool use, handler executes, loop continues,
  final text returned on turn 2
- Multi-turn with multiple tool uses in one assistant message
- Loop exhaustion: max_turns reached before final text
- Beta header + context_management forwarding
- Memory safety preamble prepended to system
- Error path: handler returns is_error=True, loop continues
- Token usage accumulation across turns
- Memory ops recorded in observability list

No real Anthropic SDK imports. Mock client objects with the minimal
shape the loop needs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.agent_loop import (
    _BETA_HEADERS,
    _MEMORY_SAFETY_PREAMBLE,
    _MEMORY_TOOL_DECLARATION,
    AgentLoopResponse,
    run_memory_loop,
)
from app.memory.anthropic_memory_tool import MemoryToolHandler


# ── Mock content block builders ──────────────────────────────────────────
#
# Minimal shapes matching what Anthropic's SDK returns. We use dict
# shape throughout because the loop's _block_* helpers handle both
# object and dict shapes.


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def _thinking_block(text: str) -> dict:
    return {"type": "thinking", "thinking": text}


def _tool_use_block(tu_id: str, command: str, **params: Any) -> dict:
    input_data = {"command": command}
    input_data.update(params)
    return {
        "type": "tool_use",
        "id": tu_id,
        "name": "memory",
        "input": input_data,
    }


def _mock_response(content: list[dict], input_tokens: int = 50, output_tokens: int = 20, model: str = "claude-sonnet-4-6"):
    """Build a mock Anthropic response object."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    response = MagicMock()
    response.content = content
    response.usage = usage
    response.model = model
    return response


def _mock_client(responses: list):
    """Build a mock client whose beta.messages.create returns responses in order."""
    client = MagicMock()
    client.beta = MagicMock()
    client.beta.messages = MagicMock()
    client.beta.messages.create = AsyncMock(side_effect=responses)
    return client


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def handler(tmp_path: Path) -> MemoryToolHandler:
    return MemoryToolHandler(
        base_path=tmp_path, agent_id="TestAgent", check_poisoning=True
    )


# ── Single-turn: no tool uses ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_single_turn_text_only_response(handler: MemoryToolHandler):
    """The assistant returns text directly — loop exits after 1 turn."""
    responses = [
        _mock_response([_text_block("Here is the answer: 42")])
    ]
    client = _mock_client(responses)

    result = await run_memory_loop(
        client=client,
        system="You are a helpful assistant",
        messages=[{"role": "user", "content": "What is the answer?"}],
        memory_handler=handler,
    )

    assert isinstance(result, AgentLoopResponse)
    assert result.text == "Here is the answer: 42"
    assert result.turns == 1
    assert result.tool_use_count == 0
    assert result.memory_ops == []
    assert result.stopped_early is False
    assert result.tokens_input == 50
    assert result.tokens_output == 20


# ── Beta header + tool declaration forwarded ─────────────────────────────


@pytest.mark.asyncio
async def test_beta_header_always_forwarded(handler: MemoryToolHandler):
    responses = [_mock_response([_text_block("done")])]
    client = _mock_client(responses)

    await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "go"}],
        memory_handler=handler,
    )

    call_kwargs = client.beta.messages.create.await_args.kwargs
    assert call_kwargs["betas"] == _BETA_HEADERS
    assert _MEMORY_TOOL_DECLARATION in call_kwargs["tools"]


@pytest.mark.asyncio
async def test_context_management_forwarded_when_set(handler: MemoryToolHandler):
    responses = [_mock_response([_text_block("done")])]
    client = _mock_client(responses)

    ctx = {"edits": [{"type": "clear_tool_uses_20250919"}]}
    await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "go"}],
        memory_handler=handler,
        context_management=ctx,
    )

    call_kwargs = client.beta.messages.create.await_args.kwargs
    assert call_kwargs["context_management"] == ctx


@pytest.mark.asyncio
async def test_context_management_omitted_when_none(handler: MemoryToolHandler):
    responses = [_mock_response([_text_block("done")])]
    client = _mock_client(responses)

    await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "go"}],
        memory_handler=handler,
        context_management=None,
    )

    call_kwargs = client.beta.messages.create.await_args.kwargs
    assert "context_management" not in call_kwargs


# ── Memory safety preamble injected ──────────────────────────────────────


@pytest.mark.asyncio
async def test_safety_preamble_prepended_to_system(handler: MemoryToolHandler):
    responses = [_mock_response([_text_block("done")])]
    client = _mock_client(responses)

    await run_memory_loop(
        client=client,
        system="You are a compliance agent.",
        messages=[{"role": "user", "content": "go"}],
        memory_handler=handler,
    )

    call_kwargs = client.beta.messages.create.await_args.kwargs
    system_text = call_kwargs["system"]
    assert system_text.startswith(_MEMORY_SAFETY_PREAMBLE)
    assert "You are a compliance agent." in system_text


# ── Multi-turn: one tool use, then final text ────────────────────────────


@pytest.mark.asyncio
async def test_multi_turn_one_tool_use(handler: MemoryToolHandler, tmp_path: Path):
    """Turn 1: assistant calls view. Turn 2: assistant returns text."""
    responses = [
        _mock_response(
            [_tool_use_block("toolu_1", "view", path="/memories")],
            input_tokens=100,
            output_tokens=30,
        ),
        _mock_response(
            [_text_block("I saw the memories.")],
            input_tokens=120,
            output_tokens=10,
        ),
    ]
    client = _mock_client(responses)

    result = await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "check memories"}],
        memory_handler=handler,
        max_turns=5,
    )

    assert result.turns == 2
    assert result.tool_use_count == 1
    assert result.text == "I saw the memories."
    assert result.stopped_early is False
    # Token counts accumulate across turns
    assert result.tokens_input == 220
    assert result.tokens_output == 40
    assert len(result.memory_ops) == 1
    assert result.memory_ops[0]["command"] == "view"


# ── Multi-turn: tool writes and reads ────────────────────────────────────


@pytest.mark.asyncio
async def test_multi_turn_create_then_read(handler: MemoryToolHandler):
    """Assistant creates a file, then on turn 2 reads it back."""
    responses = [
        _mock_response(
            [_tool_use_block("toolu_1", "create", path="/memories/note.md", file_text="hello")],
        ),
        _mock_response(
            [_tool_use_block("toolu_2", "view", path="/memories/note.md")],
        ),
        _mock_response(
            [_text_block("Confirmed: file contains 'hello'")],
        ),
    ]
    client = _mock_client(responses)

    result = await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "save note"}],
        memory_handler=handler,
        max_turns=5,
    )

    assert result.turns == 3
    assert result.tool_use_count == 2
    assert result.text.startswith("Confirmed:")
    # Both commands recorded
    commands = [op["command"] for op in result.memory_ops]
    assert commands == ["create", "view"]
    # The create should succeed, the view should succeed
    assert all(not op["is_error"] for op in result.memory_ops)
    # File actually exists on disk
    assert (handler.memory_root / "note.md").exists()


# ── Multi-turn: multiple tool uses in one assistant message ──────────────


@pytest.mark.asyncio
async def test_multiple_tool_uses_in_one_message(handler: MemoryToolHandler):
    responses = [
        _mock_response(
            [
                _tool_use_block("toolu_a", "create", path="/memories/a.md", file_text="A"),
                _tool_use_block("toolu_b", "create", path="/memories/b.md", file_text="B"),
            ],
        ),
        _mock_response([_text_block("Both created.")]),
    ]
    client = _mock_client(responses)

    result = await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "create two files"}],
        memory_handler=handler,
    )

    assert result.tool_use_count == 2
    assert len(result.memory_ops) == 2
    assert (handler.memory_root / "a.md").exists()
    assert (handler.memory_root / "b.md").exists()


# ── Error path: tool returns is_error ────────────────────────────────────


@pytest.mark.asyncio
async def test_tool_error_does_not_abort_loop(handler: MemoryToolHandler):
    """When a tool use errors (path traversal), the loop continues."""
    responses = [
        _mock_response(
            [_tool_use_block("toolu_1", "view", path="/memories/../escaped")],
        ),
        _mock_response([_text_block("I saw the error and recovered.")]),
    ]
    client = _mock_client(responses)

    result = await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "go"}],
        memory_handler=handler,
    )

    # Loop completes normally; the is_error flag is carried in memory_ops
    assert result.stopped_early is False
    assert result.tool_use_count == 1
    assert result.memory_ops[0]["is_error"] is True
    assert result.text == "I saw the error and recovered."


# ── Loop exhaustion: max_turns reached ───────────────────────────────────


@pytest.mark.asyncio
async def test_max_turns_exhaustion(handler: MemoryToolHandler):
    """Model keeps calling tools past max_turns — loop stops with stopped_early."""
    # All responses are tool uses, none are final text
    infinite_tool_use = [
        _mock_response([_tool_use_block(f"toolu_{i}", "view", path="/memories")])
        for i in range(20)
    ]
    client = _mock_client(infinite_tool_use)

    result = await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "loop forever"}],
        memory_handler=handler,
        max_turns=3,
    )

    assert result.turns == 3
    assert result.stopped_early is True
    assert result.tool_use_count == 3


@pytest.mark.asyncio
async def test_hard_turn_cap(handler: MemoryToolHandler):
    """Caller passes max_turns=100 but the hard cap is 10."""
    infinite_tool_use = [
        _mock_response([_tool_use_block(f"toolu_{i}", "view", path="/memories")])
        for i in range(50)
    ]
    client = _mock_client(infinite_tool_use)

    result = await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "loop forever"}],
        memory_handler=handler,
        max_turns=100,  # caller requests 100
    )

    # Hard cap is 10
    assert result.turns == 10
    assert result.stopped_early is True


# ── Thinking blocks captured ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_thinking_blocks_captured(handler: MemoryToolHandler):
    responses = [
        _mock_response(
            [
                _thinking_block("Let me think about this..."),
                _text_block("The answer is 42"),
            ]
        )
    ]
    client = _mock_client(responses)

    result = await run_memory_loop(
        client=client,
        system="s",
        messages=[{"role": "user", "content": "answer"}],
        memory_handler=handler,
    )

    assert result.text == "The answer is 42"
    assert "Let me think" in result.thinking


# ── to_dict serialization ────────────────────────────────────────────────


def test_agent_loop_response_to_dict():
    resp = AgentLoopResponse(
        text="hi",
        tokens_input=10,
        tokens_output=5,
        model="claude-sonnet-4-6",
        turns=1,
        tool_use_count=0,
        memory_ops=[],
        stopped_early=False,
    )
    d = resp.to_dict()
    assert d["text"] == "hi"
    assert d["tokens_input"] == 10
    assert d["turns"] == 1
    assert d["provider"] == "claude"
    assert d["stopped_early"] is False


# ── Messages list mutation (the loop appends in-place) ──────────────────


@pytest.mark.asyncio
async def test_messages_appended_during_loop(handler: MemoryToolHandler):
    """The loop appends assistant + tool_result messages so the caller
    sees the full transcript after the call returns."""
    responses = [
        _mock_response([_tool_use_block("toolu_1", "view", path="/memories")]),
        _mock_response([_text_block("done")]),
    ]
    client = _mock_client(responses)

    messages: list[dict] = [{"role": "user", "content": "start"}]
    initial_len = len(messages)

    await run_memory_loop(
        client=client,
        system="s",
        messages=messages,
        memory_handler=handler,
    )

    # Original + assistant turn (with tool_use) + user turn (with tool_result)
    assert len(messages) == initial_len + 2
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    # The last user message is the tool_result
    tool_result_content = messages[2]["content"]
    assert isinstance(tool_result_content, list)
    assert tool_result_content[0]["type"] == "tool_result"
