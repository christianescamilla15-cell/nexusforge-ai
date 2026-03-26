"""Tests for the 3-tier memory system (Session 3)."""

import pytest
from app.memory.working import WorkingMemory, _MAX_CONVERSATION_HISTORY


class TestWorkingMemorySetGetClear:
    """Core dict API tests."""

    def test_set_and_get(self):
        wm = WorkingMemory()
        wm.set("key1", "value1")
        assert wm.get("key1") == "value1"

    def test_get_missing_key_returns_default(self):
        wm = WorkingMemory()
        assert wm.get("nonexistent") is None
        assert wm.get("nonexistent", "fallback") == "fallback"

    def test_set_overwrites_existing(self):
        wm = WorkingMemory()
        wm.set("k", 1)
        wm.set("k", 2)
        assert wm.get("k") == 2

    def test_clear_removes_all(self):
        wm = WorkingMemory()
        wm.set("a", 1)
        wm.add_message("user", "hello")
        wm.store_tool_result("tool1", {"ok": True})
        wm.clear()
        assert wm.get("a") is None
        assert wm.get_messages() == []
        assert wm.get_tool_result("tool1") is None


class TestWorkingMemoryConversation:
    """Conversation history tests."""

    def test_add_message_and_get(self):
        wm = WorkingMemory()
        wm.add_message("user", "hi")
        wm.add_message("assistant", "hello")
        msgs = wm.get_messages()
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "content": "hi"}
        assert msgs[1] == {"role": "assistant", "content": "hello"}

    def test_conversation_respects_max_limit(self):
        wm = WorkingMemory()
        for i in range(_MAX_CONVERSATION_HISTORY + 10):
            wm.add_message("user", f"msg-{i}")
        msgs = wm.get_messages()
        assert len(msgs) == _MAX_CONVERSATION_HISTORY
        # Oldest messages should be evicted
        assert msgs[0]["content"] == "msg-10"

    def test_max_limit_is_20(self):
        assert _MAX_CONVERSATION_HISTORY == 20


class TestWorkingMemoryToolResults:
    """Tool result storage tests."""

    def test_store_and_get_tool_result(self):
        wm = WorkingMemory()
        wm.store_tool_result("search", {"results": [1, 2, 3]})
        assert wm.get_tool_result("search") == {"results": [1, 2, 3]}

    def test_get_missing_tool_result_returns_none(self):
        wm = WorkingMemory()
        assert wm.get_tool_result("unknown_tool") is None


class TestWorkingMemoryContext:
    """Context string generation tests."""

    def test_get_context_string_empty(self):
        wm = WorkingMemory()
        assert wm.get_context_string() == ""

    def test_get_context_string_with_store(self):
        wm = WorkingMemory()
        wm.set("task", "classify")
        ctx = wm.get_context_string()
        assert "[Task Context]" in ctx
        assert "task=" in ctx
        assert "classify" in ctx

    def test_get_context_string_with_messages(self):
        wm = WorkingMemory()
        wm.add_message("user", "analyze this")
        ctx = wm.get_context_string()
        assert "[Recent Messages]" in ctx
        assert "user:" in ctx

    def test_get_context_string_with_tool_results(self):
        wm = WorkingMemory()
        wm.store_tool_result("search", "found 3 items")
        ctx = wm.get_context_string()
        assert "[Tool Results]" in ctx
        assert "search:" in ctx

    def test_get_context_string_combined(self):
        wm = WorkingMemory()
        wm.set("task", "test")
        wm.add_message("user", "hello")
        wm.store_tool_result("tool1", "result1")
        ctx = wm.get_context_string()
        assert "[Task Context]" in ctx
        assert "[Recent Messages]" in ctx
        assert "[Tool Results]" in ctx

    def test_context_string_shows_last_5_messages(self):
        wm = WorkingMemory()
        for i in range(10):
            wm.add_message("user", f"message-{i}")
        ctx = wm.get_context_string()
        # Should only show last 5 in context string
        assert "message-5" in ctx
        assert "message-9" in ctx
        assert "message-0" not in ctx


class TestMemoryTiersIndependence:
    """Memory tiers should be independent."""

    def test_working_memory_independent_instance(self):
        wm1 = WorkingMemory()
        wm2 = WorkingMemory()
        wm1.set("x", 1)
        assert wm2.get("x") is None

    def test_set_task_get_task(self):
        """Using the dict API for task storage."""
        wm = WorkingMemory()
        wm.set("current_task", "Process invoices")
        assert wm.get("current_task") == "Process invoices"
