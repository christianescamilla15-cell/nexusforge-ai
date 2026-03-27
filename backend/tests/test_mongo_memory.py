"""Tests for MongoDB-backed episodic memory (polyglot persistence).

All tests mock the motor client so they run without a live MongoDB instance.
"""

from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_episode(agent_id: str = "agent-1", episode_type: str = "task_complete",
                  summary: str = "did something", outcome: str = "success"):
    """Create a sample episode document."""
    return {
        "agent_id": agent_id,
        "episode_type": episode_type,
        "summary": summary,
        "context": {},
        "outcome": outcome,
        "relevance_score": 1.0,
        "created_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC) + timedelta(days=30),
    }


class MockCursor:
    """Minimal async cursor mock with sort/limit/to_list."""

    def __init__(self, docs: list[dict]):
        self._docs = docs

    def sort(self, *args, **kwargs):
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length: int = 100):
        return self._docs[:length]


class MockAggCursor:
    """Minimal async aggregation cursor."""

    def __init__(self, docs: list[dict]):
        self._docs = docs

    async def to_list(self, length: int = 100):
        return self._docs[:length]


def _build_mock_collection(find_docs=None, agg_docs=None, insert_id=None):
    """Build a mock collection object that supports the operations we use."""
    collection = AsyncMock()
    collection.create_index = AsyncMock()

    # find()
    cursor = MockCursor(find_docs or [])
    collection.find = MagicMock(return_value=cursor)

    # aggregate()
    agg_cursor = MockAggCursor(agg_docs or [])
    collection.aggregate = MagicMock(return_value=agg_cursor)

    # insert_one()
    insert_result = MagicMock()
    insert_result.inserted_id = insert_id or "abc123"
    collection.insert_one = AsyncMock(return_value=insert_result)

    return collection


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMongoEpisodicStoreEpisode:
    """store_episode tests."""

    @pytest.mark.asyncio
    async def test_store_episode_returns_id(self):
        mock_col = _build_mock_collection(insert_id="mongo_id_123")
        with patch("app.memory.episodic_mongo.get_mongo_db") as mock_db:
            mock_db.return_value = {"agent_episodes": mock_col}

            # We need to make the dict subscription work
            db_obj = MagicMock()
            db_obj.__getitem__ = MagicMock(return_value=mock_col)
            mock_db.return_value = db_obj

            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.store_episode("agent-1", "task_complete", "finished task")

            assert result == "mongo_id_123"
            mock_col.insert_one.assert_called_once()
            doc = mock_col.insert_one.call_args[0][0]
            assert doc["agent_id"] == "agent-1"
            assert doc["episode_type"] == "task_complete"
            assert doc["summary"] == "finished task"
            assert doc["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_store_episode_custom_outcome(self):
        mock_col = _build_mock_collection(insert_id="fail_id")
        db_obj = MagicMock()
        db_obj.__getitem__ = MagicMock(return_value=mock_col)

        with patch("app.memory.episodic_mongo.get_mongo_db", return_value=db_obj):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.store_episode(
                "agent-1", "error", "something broke", outcome="failure"
            )
            assert result == "fail_id"
            doc = mock_col.insert_one.call_args[0][0]
            assert doc["outcome"] == "failure"

    @pytest.mark.asyncio
    async def test_store_episode_graceful_fallback_on_error(self):
        with patch("app.memory.episodic_mongo.get_mongo_db", side_effect=Exception("connection refused")):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.store_episode("agent-1", "task_complete", "test")
            assert result is None  # Graceful fallback


class TestMongoEpisodicRecallRecent:
    """recall_recent tests."""

    @pytest.mark.asyncio
    async def test_recall_recent_returns_episodes(self):
        episodes = [_make_episode(summary=f"ep-{i}") for i in range(3)]
        mock_col = _build_mock_collection(find_docs=episodes)
        db_obj = MagicMock()
        db_obj.__getitem__ = MagicMock(return_value=mock_col)

        with patch("app.memory.episodic_mongo.get_mongo_db", return_value=db_obj):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.recall_recent("agent-1", limit=10)
            assert len(result) == 3
            assert result[0]["summary"] == "ep-0"

    @pytest.mark.asyncio
    async def test_recall_recent_respects_limit(self):
        episodes = [_make_episode(summary=f"ep-{i}") for i in range(10)]
        mock_col = _build_mock_collection(find_docs=episodes)
        db_obj = MagicMock()
        db_obj.__getitem__ = MagicMock(return_value=mock_col)

        with patch("app.memory.episodic_mongo.get_mongo_db", return_value=db_obj):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.recall_recent("agent-1", limit=3)
            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_recall_recent_graceful_fallback(self):
        with patch("app.memory.episodic_mongo.get_mongo_db", side_effect=Exception("down")):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.recall_recent("agent-1")
            assert result == []


class TestMongoEpisodicRecallByType:
    """recall_by_type tests."""

    @pytest.mark.asyncio
    async def test_recall_by_type_filters_correctly(self):
        episodes = [_make_episode(episode_type="error", summary="e1")]
        mock_col = _build_mock_collection(find_docs=episodes)
        db_obj = MagicMock()
        db_obj.__getitem__ = MagicMock(return_value=mock_col)

        with patch("app.memory.episodic_mongo.get_mongo_db", return_value=db_obj):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.recall_by_type("agent-1", "error")
            assert len(result) == 1
            # Verify filter was passed to find()
            call_args = mock_col.find.call_args[0]
            assert call_args[0]["episode_type"] == "error"

    @pytest.mark.asyncio
    async def test_recall_by_type_graceful_fallback(self):
        with patch("app.memory.episodic_mongo.get_mongo_db", side_effect=Exception("down")):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.recall_by_type("agent-1", "error")
            assert result == []


class TestMongoEpisodicGetPatterns:
    """get_patterns tests."""

    @pytest.mark.asyncio
    async def test_get_patterns_aggregation(self):
        agg_results = [
            {"_id": "success", "count": 8, "latest": datetime.now(UTC)},
            {"_id": "failure", "count": 2, "latest": datetime.now(UTC)},
        ]
        mock_col = _build_mock_collection(agg_docs=agg_results)
        db_obj = MagicMock()
        db_obj.__getitem__ = MagicMock(return_value=mock_col)

        with patch("app.memory.episodic_mongo.get_mongo_db", return_value=db_obj):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            patterns = await mem.get_patterns("agent-1")
            assert patterns["total_episodes"] == 10
            assert patterns["success_rate"] == 0.8
            assert patterns["breakdown"]["success"] == 8
            assert patterns["breakdown"]["failure"] == 2

    @pytest.mark.asyncio
    async def test_get_patterns_empty(self):
        mock_col = _build_mock_collection(agg_docs=[])
        db_obj = MagicMock()
        db_obj.__getitem__ = MagicMock(return_value=mock_col)

        with patch("app.memory.episodic_mongo.get_mongo_db", return_value=db_obj):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            patterns = await mem.get_patterns("agent-1")
            assert patterns["total_episodes"] == 0
            assert patterns["success_rate"] == 0

    @pytest.mark.asyncio
    async def test_get_patterns_graceful_fallback(self):
        with patch("app.memory.episodic_mongo.get_mongo_db", side_effect=Exception("down")):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            patterns = await mem.get_patterns("agent-1")
            assert patterns == {"total_episodes": 0, "success_rate": 0, "breakdown": {}}


class TestMongoEpisodicSearchSimilar:
    """search_similar tests."""

    @pytest.mark.asyncio
    async def test_search_similar_returns_results(self):
        episodes = [_make_episode(summary="machine learning task")]
        mock_col = _build_mock_collection(find_docs=episodes)
        db_obj = MagicMock()
        db_obj.__getitem__ = MagicMock(return_value=mock_col)

        with patch("app.memory.episodic_mongo.get_mongo_db", return_value=db_obj):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.search_similar("agent-1", "machine learning")
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_similar_graceful_fallback(self):
        with patch("app.memory.episodic_mongo.get_mongo_db", side_effect=Exception("down")):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            result = await mem.search_similar("agent-1", "query")
            assert result == []


class TestMongoEpisodicAgentStats:
    """get_agent_stats tests."""

    @pytest.mark.asyncio
    async def test_get_agent_stats_with_data(self):
        now = datetime.now(UTC)
        agg_results = [{
            "_id": None,
            "total": 25,
            "types": ["task_complete", "error", "insight"],
            "avg_relevance": 0.85,
            "first_episode": now - timedelta(days=10),
            "last_episode": now,
        }]
        mock_col = _build_mock_collection(agg_docs=agg_results)
        db_obj = MagicMock()
        db_obj.__getitem__ = MagicMock(return_value=mock_col)

        with patch("app.memory.episodic_mongo.get_mongo_db", return_value=db_obj):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            stats = await mem.get_agent_stats("agent-1")
            assert stats["total_episodes"] == 25
            assert stats["avg_relevance"] == 0.85
            assert "task_complete" in stats["episode_types"]
            assert stats["active_since"] is not None

    @pytest.mark.asyncio
    async def test_get_agent_stats_empty(self):
        mock_col = _build_mock_collection(agg_docs=[])
        db_obj = MagicMock()
        db_obj.__getitem__ = MagicMock(return_value=mock_col)

        with patch("app.memory.episodic_mongo.get_mongo_db", return_value=db_obj):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            stats = await mem.get_agent_stats("agent-1")
            assert stats == {"total_episodes": 0}

    @pytest.mark.asyncio
    async def test_get_agent_stats_graceful_fallback(self):
        with patch("app.memory.episodic_mongo.get_mongo_db", side_effect=Exception("down")):
            from app.memory.episodic_mongo import MongoEpisodicMemory
            mem = MongoEpisodicMemory()
            stats = await mem.get_agent_stats("agent-1")
            assert stats == {"total_episodes": 0}
