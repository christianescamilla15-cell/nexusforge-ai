"""Predictive Memory — forward-looking predictions based on historical analysis.

Answers: "What WILL happen? Should we pre-route? How much will this cost?"
Consumes data from RegressiveMemory to make predictions before execution.

Capabilities:
- Fallback probability prediction (should we skip Ollama?)
- Cost/token/duration estimation before execution
- Sequence failure prediction (after A+B, will C fail?)
- Workflow cost forecasting
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PredictiveMemory:
    """Tier 4b: Forward-looking predictions based on regressive analysis."""

    _MAX_CACHE_SIZE = 500  # Evict oldest entries when exceeded

    def __init__(self):
        from app.memory.regressive import RegressiveMemory
        self._regressive = RegressiveMemory()
        self._cache: dict[str, tuple[float, dict]] = {}
        self._cache_ttl = 300  # 5 minutes

    def _get_cached(self, key: str) -> dict | None:
        """Return cached prediction if still fresh."""
        if key in self._cache:
            expiry, data = self._cache[key]
            if time.monotonic() < expiry:
                return data
            del self._cache[key]
        return None

    def _set_cached(self, key: str, data: dict):
        # Evict expired entries if cache is too large
        if len(self._cache) >= self._MAX_CACHE_SIZE:
            now = time.monotonic()
            expired = [k for k, (exp, _) in self._cache.items() if exp <= now]
            for k in expired:
                del self._cache[k]
            # If still too large after purging expired, drop oldest 20%
            if len(self._cache) >= self._MAX_CACHE_SIZE:
                sorted_keys = sorted(self._cache, key=lambda k: self._cache[k][0])
                for k in sorted_keys[:len(sorted_keys) // 5]:
                    del self._cache[k]
        self._cache[key] = (time.monotonic() + self._cache_ttl, data)

    def invalidate(self, agent_id: str):
        """Invalidate all cached predictions for an agent.

        Called by circuit breaker or after significant state changes.
        """
        keys_to_remove = [k for k in self._cache if k.startswith(agent_id)]
        for k in keys_to_remove:
            del self._cache[k]

    async def predict_execution(
        self,
        agent_id: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Predict execution outcome, cost, and duration before running.

        Returns:
            {
                "fallback_probability": 0.12,
                "error_probability": 0.03,
                "estimated_duration_sec": 2.4,
                "estimated_tokens": 850,
                "estimated_cost_usd": 0.0,
                "confidence": 0.85,
                "sample_size": 142,
                "anomalies_active": False,
                "recommendation": "proceed" | "consider_fallback" | "high_risk"
            }
        """
        cache_key = f"{agent_id}:{model or 'default'}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            stats = await self._regressive.get_rolling_stats(agent_id, "24h")
            anomalies = await self._regressive.detect_anomalies(agent_id, window="1h")
        except Exception as e:
            logger.warning("predictive.predict_execution failed: %s", e)
            return self._neutral_prediction()

        if not stats or stats.get("count", 0) == 0:
            return self._neutral_prediction()

        count = stats["count"]
        fallback_prob = stats.get("fallback_rate", 0)
        error_prob = stats.get("error_rate", 0)
        duration = stats.get("duration", {})
        tokens = stats.get("tokens", {})
        cost = stats.get("cost", {})
        has_anomalies = len(anomalies) > 0

        # Confidence based on sample size (asymptotic to 1.0)
        confidence = round(min(1.0, count / 100), 2)

        # Boost fallback probability if anomalies are active
        if has_anomalies:
            fallback_prob = min(1.0, fallback_prob * 1.5)

        # Recommendation
        combined_risk = fallback_prob + error_prob
        if combined_risk > 0.5:
            recommendation = "high_risk"
        elif combined_risk > 0.2 or has_anomalies:
            recommendation = "consider_fallback"
        else:
            recommendation = "proceed"

        prediction = {
            "fallback_probability": round(fallback_prob, 3),
            "error_probability": round(error_prob, 3),
            "estimated_duration_sec": duration.get("avg", 0),
            "estimated_tokens": int(tokens.get("avg", 0)),
            "estimated_cost_usd": cost.get("avg", 0),
            "confidence": confidence,
            "sample_size": count,
            "anomalies_active": has_anomalies,
            "recommendation": recommendation,
        }

        self._set_cached(cache_key, prediction)
        return prediction

    async def should_preempt_fallback(
        self, agent_id: str, model: str
    ) -> bool:
        """Quick decision: should we skip this provider and go to fallback?

        Used by LLMRouter before attempting Ollama. If historical data shows
        >50% fallback rate, skip directly to Groq/Claude.
        """
        try:
            prediction = await self.predict_execution(agent_id, model)
            return (
                prediction["confidence"] > 0.3
                and prediction["fallback_probability"] > 0.5
            )
        except Exception:
            return False  # When in doubt, proceed normally

    async def predict_sequence_failure(
        self,
        step_sequence: list[str],
        current_step_index: int,
    ) -> dict[str, Any]:
        """Predict failure probability for the next step in a sequence.

        Based on historical success rates of each agent, computes the
        conditional probability of the next step failing given that
        previous steps succeeded.
        """
        if current_step_index >= len(step_sequence) - 1:
            return {"next_step": None, "failure_probability": 0}

        next_agent = step_sequence[current_step_index + 1]

        try:
            stats = await self._regressive.get_rolling_stats(next_agent, "7d")
        except Exception:
            return {
                "next_step": next_agent,
                "failure_probability": 0,
                "confidence": 0,
            }

        if not stats or stats.get("count", 0) == 0:
            return {
                "next_step": next_agent,
                "failure_probability": 0,
                "confidence": 0,
            }

        error_rate = stats.get("error_rate", 0)
        fallback_rate = stats.get("fallback_rate", 0)
        failure_prob = error_rate + (fallback_rate * 0.3)  # Fallback is partial failure

        preceding = step_sequence[:current_step_index + 1]

        return {
            "next_step": next_agent,
            "failure_probability": round(failure_prob, 3),
            "conditional_on": [f"{s}:success" for s in preceding],
            "sample_size": stats["count"],
            "confidence": round(min(1.0, stats["count"] / 50), 2),
        }

    async def get_cost_forecast(
        self, workflow_steps: list[str]
    ) -> dict[str, Any]:
        """Forecast total cost/tokens/duration for an entire workflow.

        Sums predicted values for each step.
        """
        per_step = []
        total_cost = 0.0
        total_tokens = 0
        total_duration = 0.0

        for step in workflow_steps:
            try:
                pred = await self.predict_execution(step)
            except Exception:
                pred = self._neutral_prediction()

            per_step.append({
                "agent": step,
                "estimated_cost_usd": pred["estimated_cost_usd"],
                "estimated_tokens": pred["estimated_tokens"],
                "estimated_duration_sec": pred["estimated_duration_sec"],
                "fallback_probability": pred["fallback_probability"],
            })
            total_cost += pred["estimated_cost_usd"]
            total_tokens += pred["estimated_tokens"]
            total_duration += pred["estimated_duration_sec"]

        return {
            "total_estimated_cost_usd": round(total_cost, 4),
            "total_estimated_tokens": total_tokens,
            "total_estimated_duration_sec": round(total_duration, 2),
            "step_count": len(workflow_steps),
            "per_step": per_step,
        }

    @staticmethod
    def _neutral_prediction() -> dict:
        """Return neutral prediction when no data is available."""
        return {
            "fallback_probability": 0.0,
            "error_probability": 0.0,
            "estimated_duration_sec": 0,
            "estimated_tokens": 0,
            "estimated_cost_usd": 0.0,
            "confidence": 0.0,
            "sample_size": 0,
            "anomalies_active": False,
            "recommendation": "proceed",
        }
