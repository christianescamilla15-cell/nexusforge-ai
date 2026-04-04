"""RouterAgent — fast keyword-based routing with LLM fallback for ambiguous tasks.

Uses keyword similarity for instant routing (<1ms, $0 cost).
Falls back to LLM only when confidence is below threshold.
"""

import json
import logging
import re

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent, list_agents

logger = logging.getLogger(__name__)

# Keyword routes: agent_type -> list of trigger keywords/patterns
_KEYWORD_ROUTES: dict[str, list[str]] = {
    "classifier":  ["classify", "categorize", "category", "type of", "what kind", "document type"],
    "extractor":   ["extract", "entities", "find names", "find dates", "parse", "pull out", "ner"],
    "summarizer":  ["summarize", "summary", "condense", "shorten", "tldr", "brief"],
    "sentiment":   ["sentiment", "emotion", "feel", "opinion", "positive", "negative", "tone"],
    "translator":  ["translate", "translation", "spanish", "english", "idioma", "language"],
    "ocr":         ["ocr", "scan", "image", "pdf", "handwriting", "receipt", "invoice scan"],
    "normalizer":  ["normalize", "standardize", "format", "deduplicate", "clean data", "dedup"],
    "analyzer":    ["analyze", "analysis", "trend", "anomaly", "statistics", "insight", "pattern"],
    "enricher":    ["enrich", "augment", "context", "additional info", "cross-reference", "lookup"],
    "compliance":  ["compliance", "regulation", "gdpr", "hipaa", "pii", "legal", "audit", "privacy"],
    "knowledge":   ["knowledge", "answer", "question", "faq", "document search", "rag", "ask"],
    "validator":   ["validate", "verify", "check", "quality", "correct", "accuracy"],
    "reporter":    ["report", "generate report", "executive summary", "findings", "deliverable"],
    "scraper":     ["scrape", "crawl", "web", "url", "website", "fetch page", "download"],
    "researcher":  ["research", "investigate", "study", "find out", "market", "competitive"],
    "scheduler":   ["schedule", "cron", "recurring", "appointment", "calendar", "when"],
    "monitor":     ["monitor", "alert", "threshold", "health", "uptime", "metric", "dashboard"],
    "planner":     ["plan", "decompose", "break down", "steps", "workflow", "pipeline", "orchestrate"],
    "repair":      ["repair", "fix", "heal", "error", "diagnose", "debug", "failed"],
    "critic":      ["critique", "evaluate", "review", "score", "feedback", "quality check"],
    "webhook":     ["webhook", "notify", "callback", "post to", "send to", "deliver"],
}

ROUTE_PROMPT = """Analyze the following task and determine which agent(s) should handle it.

Available agents: {agents}

Respond ONLY with valid JSON (no markdown):
{{"recommended_agents": ["<agent_type1>", "<agent_type2>"], "reasoning": "<explanation>", "confidence": <0.0-1.0>}}

Task:
{task}"""

# Confidence threshold: below this, fall back to LLM
_KEYWORD_CONFIDENCE_THRESHOLD = 0.4


def _keyword_route(task: str, available_agents: list[str]) -> dict | None:
    """Fast keyword-based routing. Returns result dict or None if low confidence."""
    task_lower = task.lower()
    scores: dict[str, float] = {}

    for agent_type, keywords in _KEYWORD_ROUTES.items():
        if agent_type not in available_agents:
            continue
        hits = sum(1 for kw in keywords if kw in task_lower)
        if hits > 0:
            scores[agent_type] = hits / len(keywords)

    if not scores:
        return None

    # Sort by score descending, take top matches
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_score = ranked[0][1]

    if top_score < _KEYWORD_CONFIDENCE_THRESHOLD:
        return None  # too ambiguous, use LLM

    # Take agents with score >= 50% of top score
    threshold = top_score * 0.5
    recommended = [agent for agent, score in ranked if score >= threshold][:5]

    return {
        "recommended_agents": recommended,
        "reasoning": f"Keyword match (top score: {top_score:.2f})",
        "confidence": min(top_score * 1.5, 0.95),  # scale up but cap at 0.95
        "_routing_method": "keyword",
    }


class RouterAgent(BaseAgent):
    name = "RouterAgent"
    agent_type = "router_agent"
    description = "Fast keyword-based routing with LLM fallback for ambiguous tasks."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        task = input_data.get("task", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not task:
            return AgentResult(
                output={
                    "recommended_agents": ["classifier", "extractor", "summarizer"],
                    "reasoning": "Demo mode — standard document processing pipeline",
                    "confidence": 0.85,
                    "_routing_method": "demo",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        available = list_agents()

        # Layer 1: Fast keyword routing (instant, $0)
        keyword_result = _keyword_route(task, available)
        if keyword_result:
            logger.info("RouterAgent: keyword match → %s", keyword_result["recommended_agents"])
            return AgentResult(
                output=keyword_result,
                tokens_used=0, cost_usd=0.0,
                provider="local", model="keyword-router",
            )

        # Layer 2: LLM routing (for ambiguous/complex tasks)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Route tasks to appropriate agents.")},
            {"role": "user", "content": ROUTE_PROMPT.format(agents=", ".join(available), task=task[:2000])},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.2, max_tokens=512)
            parsed = clean_llm_json(resp.text)
            parsed["_routing_method"] = "llm"
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("RouterAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "recommended_agents": ["classifier"],
                    "reasoning": f"Fallback: {exc}",
                    "confidence": 0.3,
                    "_routing_method": "fallback",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )


register_agent("router_agent", RouterAgent())
