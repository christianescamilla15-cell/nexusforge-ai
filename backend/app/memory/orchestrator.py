"""OrchestratorMemory — central memory hub accessible by the orchestrator (Claude).

Provides:
  - read_all_agents()     → full memory snapshot of every agent
  - inject_context()      → push knowledge into a specific agent's memory
  - get_experience_feed() → chronological experience log across all agents
  - get_agent_profile()   → aggregated stats + recent episodes for one agent
  - document_session()    → record an orchestrator-level session note
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.memory.manager import MemoryManager
from app.memory.episodic_mongo import MongoEpisodicMemory

logger = logging.getLogger(__name__)

_ALL_AGENTS = [
    "ClassifierAgent", "ExtractorAgent", "SummarizerAgent", "AnalyzerAgent",
    "EnricherAgent", "ValidatorAgent", "ReporterAgent", "RepairAgent",
    "NormalizerAgent", "ResearcherAgent", "TranslatorAgent", "ComplianceAgent",
    "MonitorAgent", "RouterAgent", "CriticAgent", "PlannerAgent",
    "KnowledgeAgent", "ScraperAgent", "OCRAgent", "SentimentAgent",
    "SchedulerAgent", "WebhookAgent", "JudgeAgent",
]


class OrchestratorMemory:
    """Central memory interface for the orchestrator.

    The orchestrator (Claude via this interface) can:
    - Read the full experience history of any agent
    - Inject context/knowledge into any agent
    - Document sessions and decisions for future recall
    - Get a system-wide experience snapshot
    """

    def __init__(self):
        self._manager = MemoryManager()
        self._mongo = MongoEpisodicMemory()

    # ── Read ────────────────────────────────────────────────────────────────

    async def read_all_agents(self, limit_per_agent: int = 5) -> dict[str, Any]:
        """Return recent episodes for every registered agent."""
        snapshot = {}
        for agent_id in _ALL_AGENTS:
            episodes = await self._mongo.recall_recent(agent_id, limit=limit_per_agent)
            if not episodes:
                episodes = await self._manager.episodic.recall_recent(agent_id, limit=limit_per_agent)
            if episodes:
                snapshot[agent_id] = episodes
        return snapshot

    async def get_agent_profile(self, agent_id: str) -> dict[str, Any]:
        """Full profile: recent episodes + patterns + stats + analytics + predictions."""
        recent = await self._mongo.recall_recent(agent_id, limit=20)
        patterns = await self._mongo.get_patterns(agent_id)
        stats = await self._mongo.get_agent_stats(agent_id)
        memories = await self._manager.semantic.recall(agent_id, agent_id, top_k=10)

        # Tier 4a: regressive analytics
        rolling_stats = {}
        anomalies = []
        correlations = {}
        try:
            rolling_stats = await self._manager.regressive.get_rolling_stats(agent_id, "24h")
            anomalies = await self._manager.regressive.detect_anomalies(agent_id, window="1h")
            correlations = await self._manager.regressive.get_failure_correlations(agent_id, "7d")
        except Exception:
            pass

        # Tier 4b: predictive
        predictions = {}
        try:
            predictions = await self._manager.predictive.predict_execution(agent_id)
        except Exception:
            pass

        return {
            "agent_id": agent_id,
            "recent_episodes": recent,
            "patterns": patterns,
            "stats": stats,
            "semantic_memories": memories,
            "rolling_stats_24h": rolling_stats,
            "active_anomalies": anomalies,
            "failure_correlations": correlations,
            "predictions": predictions,
            "retrieved_at": time.time(),
        }

    async def get_experience_feed(self, limit: int = 50) -> list[dict]:
        """Chronological experience feed across ALL agents — most recent first."""
        all_episodes = []
        for agent_id in _ALL_AGENTS:
            episodes = await self._mongo.recall_recent(agent_id, limit=10)
            for ep in episodes:
                ep["_agent_id"] = agent_id
                all_episodes.append(ep)

        # Sort by timestamp descending
        all_episodes.sort(
            key=lambda e: e.get("created_at", e.get("timestamp", e.get("stored_at", 0))),
            reverse=True,
        )
        return all_episodes[:limit]

    # ── Write ───────────────────────────────────────────────────────────────

    async def inject_context(
        self,
        agent_id: str,
        knowledge: str,
        source: str = "orchestrator",
        tier: str = "episodic",
    ) -> bool:
        """Inject knowledge into an agent's memory from the orchestrator."""
        try:
            await self._manager.remember(
                agent_id=agent_id,
                text=knowledge,
                tier=tier,
                metadata={
                    "type": "orchestrator_injection",
                    "source": source,
                    "injected_at": time.time(),
                },
            )
            logger.info("Orchestrator injected context into %s (%s)", agent_id, tier)
            return True
        except Exception as exc:
            logger.error("inject_context failed for %s: %s", agent_id, exc)
            return False

    async def inject_to_all(self, knowledge: str, source: str = "orchestrator") -> dict[str, bool]:
        """Broadcast knowledge to all agents at once."""
        results = {}
        for agent_id in _ALL_AGENTS:
            results[agent_id] = await self.inject_context(agent_id, knowledge, source)
        return results

    async def document_session(
        self,
        title: str,
        summary: str,
        decisions: list[str] | None = None,
        agents_involved: list[str] | None = None,
    ) -> bool:
        """Record an orchestrator-level session note for future recall."""
        try:
            doc = {
                "title": title,
                "summary": summary,
                "decisions": decisions or [],
                "agents_involved": agents_involved or [],
                "documented_at": time.time(),
            }
            # Store in orchestrator's own memory + semantic for similarity search
            await self._manager.remember(
                agent_id="Orchestrator",
                text=f"{title}: {summary}",
                tier="episodic,semantic",
                metadata={**doc, "type": "session_document"},
            )
            logger.info("Orchestrator documented session: %s", title)
            return True
        except Exception as exc:
            logger.error("document_session failed: %s", exc)
            return False

    async def get_orchestrator_log(self, limit: int = 20) -> list[dict]:
        """Retrieve orchestrator's own session documents."""
        return await self._mongo.recall_recent("Orchestrator", limit=limit)


# Module-level singleton
_orchestrator_memory: OrchestratorMemory | None = None


def get_orchestrator_memory() -> OrchestratorMemory:
    global _orchestrator_memory
    if _orchestrator_memory is None:
        _orchestrator_memory = OrchestratorMemory()
    return _orchestrator_memory
