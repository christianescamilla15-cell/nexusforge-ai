"""Unified memory manager — wraps all three memory tiers."""

from __future__ import annotations

import logging
from typing import Any

from app.memory.working import WorkingMemory
from app.memory.episodic import EpisodicMemory
from app.memory.semantic import SemanticMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """Single entry-point for agent memory across all three tiers.

    * **working**  — in-process dict (tier 1)
    * **episodic** — Redis with 30-day TTL (tier 2)
    * **semantic** — pgvector long-term store (tier 3)
    """

    def __init__(self) -> None:
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()

    # --- unified write ---

    async def remember(
        self,
        agent_id: str,
        text: str,
        tier: str = "working",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store *text* in the requested tier (or multiple comma-separated)."""
        tiers = [t.strip() for t in tier.split(",")]
        for t in tiers:
            if t == "working":
                self.working.set(f"last_{agent_id}", text)
            elif t == "episodic":
                await self.episodic.store_episode(
                    agent_id=agent_id,
                    episode_type=metadata.get("type", "info") if metadata else "info",
                    summary=text,
                    context=metadata,
                )
            elif t == "semantic":
                await self.semantic.store(agent_id, text, metadata)
            else:
                logger.warning("Unknown memory tier: %s", t)

    # --- unified read ---

    async def recall(
        self,
        agent_id: str,
        query: str,
        tiers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Search across requested tiers and return combined results."""
        tiers = tiers or ["working", "episodic", "semantic"]
        results: dict[str, Any] = {}

        if "working" in tiers:
            ctx = self.working.get_context_string()
            if ctx:
                results["working"] = ctx

        if "episodic" in tiers:
            episodes = await self.episodic.recall_recent(agent_id, limit=10)
            if episodes:
                results["episodic"] = episodes

        if "semantic" in tiers:
            memories = await self.semantic.recall(agent_id, query, top_k=5)
            if memories:
                results["semantic"] = memories

        return results

    # --- context builder ---

    async def build_context(self, agent_id: str, task: str) -> str:
        """Combine relevant memories from all tiers into a single context
        string suitable for injection into an LLM prompt."""
        parts: list[str] = []

        # Tier 1 — working
        working_ctx = self.working.get_context_string()
        if working_ctx:
            parts.append(f"## Working Memory\n{working_ctx}")

        # Tier 2 — episodic
        episodes = await self.episodic.recall_recent(agent_id, limit=5)
        if episodes:
            ep_lines = [f"- [{e.get('type')}] {e.get('summary', '')[:200]}" for e in episodes]
            parts.append("## Recent Episodes\n" + "\n".join(ep_lines))

        # Tier 3 — semantic
        memories = await self.semantic.recall(agent_id, task, top_k=3)
        if memories:
            sem_lines = [
                f"- (sim={m['similarity']:.2f}) {m['content'][:200]}"
                for m in memories
            ]
            parts.append("## Related Knowledge\n" + "\n".join(sem_lines))

        return "\n\n".join(parts) if parts else ""
