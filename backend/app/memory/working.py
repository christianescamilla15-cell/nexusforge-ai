"""Working memory — in-process, per-execution context store."""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

_MAX_CONVERSATION_HISTORY = 20


class WorkingMemory:
    """Tier-1 memory: fast, ephemeral, scoped to a single execution.

    Stores current task context, recent conversation history, and active
    tool results in a plain dict.  Destroyed when the execution ends.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._conversation: deque[dict] = deque(maxlen=_MAX_CONVERSATION_HISTORY)
        self._tool_results: dict[str, Any] = {}

    # --- core dict API ---

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()
        self._conversation.clear()
        self._tool_results.clear()

    # --- conversation history ---

    def add_message(self, role: str, content: str) -> None:
        self._conversation.append({"role": role, "content": content})

    def get_messages(self) -> list[dict]:
        return list(self._conversation)

    # --- tool results ---

    def store_tool_result(self, tool_name: str, result: Any) -> None:
        self._tool_results[tool_name] = result

    def get_tool_result(self, tool_name: str) -> Any | None:
        return self._tool_results.get(tool_name)

    # --- context export ---

    def get_context_string(self) -> str:
        """Combine all working memory into a single context string for LLM prompts."""
        parts: list[str] = []

        if self._store:
            items = ", ".join(f"{k}={v!r}" for k, v in self._store.items())
            parts.append(f"[Task Context] {items}")

        if self._conversation:
            recent = list(self._conversation)[-5:]
            msgs = " | ".join(f"{m['role']}: {m['content'][:120]}" for m in recent)
            parts.append(f"[Recent Messages] {msgs}")

        if self._tool_results:
            tools = ", ".join(f"{k}: {str(v)[:80]}" for k, v in self._tool_results.items())
            parts.append(f"[Tool Results] {tools}")

        return "\n".join(parts) if parts else ""
