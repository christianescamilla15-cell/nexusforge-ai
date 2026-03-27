"""Episodic memory backed by MongoDB — demonstrates polyglot persistence.
Falls back to Redis-based episodic memory if MongoDB is unavailable."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db.mongo_client import get_mongo_db

logger = logging.getLogger(__name__)


class MongoEpisodicMemory:
    """Medium-term memory stored in MongoDB with TTL index.

    Collection: agent_episodes
    Document schema:
    {
        agent_id: str,
        episode_type: str,  # "task_complete", "error", "insight", "pattern"
        summary: str,
        context: dict,
        outcome: str,  # "success" | "failure"
        relevance_score: float,  # 0.0 - 1.0
        created_at: datetime,
        expires_at: datetime,  # TTL: 30 days
    }
    """

    COLLECTION = "agent_episodes"
    TTL_DAYS = 30

    async def _get_collection(self):
        db = await get_mongo_db()
        collection = db[self.COLLECTION]
        # Ensure TTL index exists (MongoDB auto-deletes expired docs)
        await collection.create_index("expires_at", expireAfterSeconds=0)
        await collection.create_index([("agent_id", 1), ("created_at", -1)])
        await collection.create_index([("agent_id", 1), ("episode_type", 1)])
        return collection

    async def store_episode(
        self,
        agent_id: str,
        episode_type: str,
        summary: str,
        context: dict[str, Any] | None = None,
        outcome: str = "success",
    ) -> str | None:
        """Store a new episode in MongoDB."""
        try:
            collection = await self._get_collection()
            doc = {
                "agent_id": agent_id,
                "episode_type": episode_type,
                "summary": summary,
                "context": context or {},
                "outcome": outcome,
                "relevance_score": 1.0,
                "created_at": datetime.now(UTC),
                "expires_at": datetime.now(UTC) + timedelta(days=self.TTL_DAYS),
            }
            result = await collection.insert_one(doc)
            return str(result.inserted_id)
        except Exception as exc:
            logger.warning("MongoEpisodicMemory.store_episode failed: %s", exc)
            return None  # Graceful fallback

    async def recall_recent(self, agent_id: str, limit: int = 10) -> list[dict]:
        """Retrieve most recent episodes for an agent."""
        try:
            collection = await self._get_collection()
            cursor = collection.find(
                {"agent_id": agent_id},
                {"_id": 0},
            ).sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as exc:
            logger.warning("MongoEpisodicMemory.recall_recent failed: %s", exc)
            return []

    async def recall_by_type(
        self, agent_id: str, episode_type: str, limit: int = 10
    ) -> list[dict]:
        """Retrieve episodes filtered by type."""
        try:
            collection = await self._get_collection()
            cursor = collection.find(
                {"agent_id": agent_id, "episode_type": episode_type},
                {"_id": 0},
            ).sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as exc:
            logger.warning("MongoEpisodicMemory.recall_by_type failed: %s", exc)
            return []

    async def get_patterns(self, agent_id: str) -> dict:
        """Analyze success/failure patterns from episode history."""
        try:
            collection = await self._get_collection()
            pipeline = [
                {"$match": {"agent_id": agent_id}},
                {
                    "$group": {
                        "_id": "$outcome",
                        "count": {"$sum": 1},
                        "latest": {"$max": "$created_at"},
                    }
                },
            ]
            results = await collection.aggregate(pipeline).to_list(length=10)
            total = sum(r["count"] for r in results)
            success = next(
                (r["count"] for r in results if r["_id"] == "success"), 0
            )
            return {
                "total_episodes": total,
                "success_rate": round(success / total, 2) if total > 0 else 0,
                "breakdown": {r["_id"]: r["count"] for r in results},
            }
        except Exception as exc:
            logger.warning("MongoEpisodicMemory.get_patterns failed: %s", exc)
            return {"total_episodes": 0, "success_rate": 0, "breakdown": {}}

    async def search_similar(
        self, agent_id: str, query: str, limit: int = 5
    ) -> list[dict]:
        """Text search across episode summaries (uses MongoDB text index)."""
        try:
            collection = await self._get_collection()
            # Ensure text index
            await collection.create_index([("summary", "text")])
            cursor = collection.find(
                {"agent_id": agent_id, "$text": {"$search": query}},
                {"_id": 0, "score": {"$meta": "textScore"}},
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as exc:
            logger.warning("MongoEpisodicMemory.search_similar failed: %s", exc)
            return []

    async def get_agent_stats(self, agent_id: str) -> dict:
        """Get aggregated stats for an agent's episode history."""
        try:
            collection = await self._get_collection()
            pipeline = [
                {"$match": {"agent_id": agent_id}},
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "types": {"$addToSet": "$episode_type"},
                        "avg_relevance": {"$avg": "$relevance_score"},
                        "first_episode": {"$min": "$created_at"},
                        "last_episode": {"$max": "$created_at"},
                    }
                },
            ]
            results = await collection.aggregate(pipeline).to_list(length=1)
            if results:
                r = results[0]
                return {
                    "total_episodes": r["total"],
                    "episode_types": r["types"],
                    "avg_relevance": round(r["avg_relevance"], 2),
                    "active_since": (
                        r["first_episode"].isoformat()
                        if r["first_episode"]
                        else None
                    ),
                    "last_activity": (
                        r["last_episode"].isoformat()
                        if r["last_episode"]
                        else None
                    ),
                }
            return {"total_episodes": 0}
        except Exception as exc:
            logger.warning("MongoEpisodicMemory.get_agent_stats failed: %s", exc)
            return {"total_episodes": 0}
