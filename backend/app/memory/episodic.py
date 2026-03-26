"""Episodic memory — Redis-backed medium-term agent experience store."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from app.db.client import get_redis

logger = logging.getLogger(__name__)

_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


class EpisodicMemory:
    """Tier-2 memory: stores task summaries, success/failure patterns,
    and tool usage stats in Redis with a 30-day TTL."""

    # --- store ---

    async def store_episode(
        self,
        agent_id: str,
        episode_type: str,
        summary: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Save an episode to Redis.

        Returns the generated episode_id.
        """
        episode_id = uuid.uuid4().hex[:12]
        key = f"memory:episodic:{agent_id}:{episode_id}"
        payload = {
            "episode_id": episode_id,
            "agent_id": agent_id,
            "type": episode_type,
            "summary": summary,
            "context": json.dumps(context or {}),
            "timestamp": time.time(),
        }
        try:
            redis = await get_redis()
            await redis.hset(key, mapping=payload)
            await redis.expire(key, _TTL_SECONDS)
            # Also push to a per-agent timeline for easy recall
            timeline_key = f"memory:episodic:{agent_id}:_timeline"
            await redis.lpush(timeline_key, key)
            await redis.ltrim(timeline_key, 0, 499)  # keep last 500
            await redis.expire(timeline_key, _TTL_SECONDS)
        except Exception as exc:
            logger.warning("EpisodicMemory.store_episode failed: %s", exc)
        return episode_id

    # --- recall ---

    async def recall_recent(self, agent_id: str, limit: int = 10) -> list[dict]:
        """Return the last *limit* episodes for an agent."""
        try:
            redis = await get_redis()
            timeline_key = f"memory:episodic:{agent_id}:_timeline"
            keys = await redis.lrange(timeline_key, 0, limit - 1)
            episodes: list[dict] = []
            for k in keys:
                raw = await redis.hgetall(k)
                if raw:
                    raw["context"] = json.loads(raw.get("context", "{}"))
                    episodes.append(raw)
            return episodes
        except Exception as exc:
            logger.warning("EpisodicMemory.recall_recent failed: %s", exc)
            return []

    async def recall_by_type(self, agent_id: str, episode_type: str) -> list[dict]:
        """Filter recalled episodes by type."""
        all_recent = await self.recall_recent(agent_id, limit=100)
        return [ep for ep in all_recent if ep.get("type") == episode_type]

    # --- analytics ---

    async def get_patterns(self, agent_id: str) -> dict:
        """Analyse success/failure rates from stored episodes."""
        episodes = await self.recall_recent(agent_id, limit=200)
        total = len(episodes)
        if total == 0:
            return {"total": 0, "success_rate": 0.0, "failure_rate": 0.0, "types": {}}

        successes = sum(1 for e in episodes if e.get("type") == "success")
        failures = sum(1 for e in episodes if e.get("type") == "failure")
        type_counts: dict[str, int] = {}
        for ep in episodes:
            t = ep.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total": total,
            "success_rate": round(successes / total, 3) if total else 0.0,
            "failure_rate": round(failures / total, 3) if total else 0.0,
            "types": type_counts,
        }
