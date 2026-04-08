"""Regressive Memory — retrospective analysis of agent execution history.

Answers: "What happened? Why? What patterns are emerging?"
Reads from MongoDB agent_episodes collection (same as MongoEpisodicMemory).

Capabilities:
- Rolling window stats (1h, 24h, 7d) per agent
- Anomaly detection (z-score based)
- Failure correlation (model, provider, tools)
- Performance trend analysis (bucketed time-series)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

WINDOW_MAP = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


class RegressiveMemory:
    """Tier 4a: Time-series analysis of historical agent performance."""

    COLLECTION = "agent_episodes"

    async def _get_collection(self):
        try:
            from app.db.mongo_client import get_mongo_db
            db = await get_mongo_db()
            return db[self.COLLECTION]
        except Exception:
            return None

    async def get_rolling_stats(
        self, agent_id: str, window: str = "24h"
    ) -> dict[str, Any]:
        """Compute rolling statistics for an agent over a time window.

        Returns avg/min/max/stddev for duration, tokens, cost,
        plus success/fallback/error rates.
        """
        col = await self._get_collection()
        if col is None:
            return {}

        delta = WINDOW_MAP.get(window, timedelta(hours=24))
        cutoff = datetime.now(timezone.utc) - delta

        try:
            cursor = col.find(
                {"agent_id": agent_id, "created_at": {"$gte": cutoff}},
                {"context": 1, "outcome": 1, "created_at": 1},
            )
            episodes = await cursor.to_list(length=5000)
        except Exception as e:
            logger.warning("regressive.get_rolling_stats failed: %s", e)
            return {}

        if not episodes:
            return {"window": window, "count": 0}

        durations = []
        tokens = []
        costs = []
        outcomes: dict[str, int] = {}

        for ep in episodes:
            ctx = ep.get("context", {})
            if isinstance(ctx, str):
                continue
            d = ctx.get("duration_sec")
            if d is not None:
                durations.append(float(d))
            t = ctx.get("tokens_used")
            if t is not None:
                tokens.append(int(t))
            c = ctx.get("cost_usd")
            if c is not None:
                costs.append(float(c))
            outcome = ctx.get("outcome", ep.get("outcome", "unknown"))
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

        total = len(episodes)
        return {
            "window": window,
            "count": total,
            "duration": _stats(durations),
            "tokens": _stats(tokens),
            "cost": _stats(costs),
            "success_rate": round(outcomes.get("success", 0) / max(total, 1), 3),
            "fallback_rate": round(outcomes.get("fallback", 0) / max(total, 1), 3),
            "error_rate": round(outcomes.get("error", 0) / max(total, 1), 3),
            "outcomes": outcomes,
        }

    async def detect_anomalies(
        self,
        agent_id: str,
        metric: str = "duration_sec",
        window: str = "24h",
        z_threshold: float = 2.0,
    ) -> list[dict]:
        """Detect anomalous executions using z-score analysis.

        Returns episodes where the given metric deviates beyond z_threshold
        standard deviations from the mean.
        """
        col = await self._get_collection()
        if col is None:
            return []

        delta = WINDOW_MAP.get(window, timedelta(hours=24))
        cutoff = datetime.now(timezone.utc) - delta

        try:
            cursor = col.find(
                {"agent_id": agent_id, "created_at": {"$gte": cutoff}},
                {"context": 1, "summary": 1, "created_at": 1},
            )
            episodes = await cursor.to_list(length=5000)
        except Exception as e:
            logger.warning("regressive.detect_anomalies failed: %s", e)
            return []

        values = []
        for ep in episodes:
            ctx = ep.get("context", {})
            if isinstance(ctx, str):
                continue
            v = ctx.get(metric)
            if v is not None:
                values.append((ep, float(v)))

        if len(values) < 5:
            return []  # Not enough data for meaningful z-scores

        nums = [v for _, v in values]
        mean = sum(nums) / len(nums)
        variance = sum((x - mean) ** 2 for x in nums) / len(nums)
        stddev = variance ** 0.5

        if stddev < 1e-9:
            return []  # All values identical

        anomalies = []
        for ep, val in values:
            z = abs(val - mean) / stddev
            if z > z_threshold:
                anomalies.append({
                    "timestamp": ep.get("created_at"),
                    "value": val,
                    "z_score": round(z, 2),
                    "mean": round(mean, 2),
                    "stddev": round(stddev, 2),
                    "summary": ep.get("summary", ""),
                })

        return sorted(anomalies, key=lambda x: -x["z_score"])

    async def get_failure_correlations(
        self, agent_id: str, window: str = "7d"
    ) -> dict[str, Any]:
        """Analyze which conditions correlate with failures.

        Groups failures by model, provider, and tools to find patterns.
        """
        col = await self._get_collection()
        if col is None:
            return {}

        delta = WINDOW_MAP.get(window, timedelta(days=7))
        cutoff = datetime.now(timezone.utc) - delta

        try:
            cursor = col.find(
                {"agent_id": agent_id, "created_at": {"$gte": cutoff}},
                {"context": 1, "outcome": 1},
            )
            episodes = await cursor.to_list(length=5000)
        except Exception as e:
            logger.warning("regressive.get_failure_correlations failed: %s", e)
            return {}

        if not episodes:
            return {}

        by_model: dict[str, dict[str, int]] = {}
        by_provider: dict[str, dict[str, int]] = {}
        by_hour: dict[int, dict[str, int]] = {}

        for ep in episodes:
            ctx = ep.get("context", {})
            if isinstance(ctx, str):
                continue
            outcome = ctx.get("outcome", ep.get("outcome", "unknown"))
            is_failure = outcome in ("error", "fallback")

            model = ctx.get("model", "unknown")
            provider = ctx.get("provider", "unknown")
            hour = ep.get("created_at", datetime.now(timezone.utc)).hour if hasattr(ep.get("created_at"), "hour") else 0

            # Model breakdown
            if model not in by_model:
                by_model[model] = {"total": 0, "failures": 0}
            by_model[model]["total"] += 1
            if is_failure:
                by_model[model]["failures"] += 1

            # Provider breakdown
            if provider not in by_provider:
                by_provider[provider] = {"total": 0, "failures": 0}
            by_provider[provider]["total"] += 1
            if is_failure:
                by_provider[provider]["failures"] += 1

            # Hour-of-day breakdown
            if hour not in by_hour:
                by_hour[hour] = {"total": 0, "failures": 0}
            by_hour[hour]["total"] += 1
            if is_failure:
                by_hour[hour]["failures"] += 1

        # Compute failure rates
        def _rate(d: dict) -> dict:
            return {k: {**v, "failure_rate": round(v["failures"] / max(v["total"], 1), 3)}
                    for k, v in d.items()}

        # Find worst conditions
        worst = []
        for dim_name, dim_data in [("model", by_model), ("provider", by_provider)]:
            for key, vals in dim_data.items():
                rate = vals["failures"] / max(vals["total"], 1)
                if rate > 0.1 and vals["total"] >= 3:
                    worst.append({
                        "dimension": dim_name,
                        "value": key,
                        "failure_rate": round(rate, 3),
                        "sample_size": vals["total"],
                    })
        worst.sort(key=lambda x: -x["failure_rate"])

        return {
            "by_model": _rate(by_model),
            "by_provider": _rate(by_provider),
            "by_hour": _rate(by_hour),
            "top_failure_conditions": worst[:5],
        }

    async def get_trend(
        self,
        agent_id: str,
        metric: str = "duration_sec",
        buckets: int = 12,
        window: str = "24h",
    ) -> list[dict]:
        """Get time-bucketed trend for a metric.

        Divides the window into N equal buckets and computes avg per bucket.
        Useful for frontend performance charts.
        """
        col = await self._get_collection()
        if col is None:
            return []

        delta = WINDOW_MAP.get(window, timedelta(hours=24))
        cutoff = datetime.now(timezone.utc) - delta
        bucket_size = delta / buckets

        try:
            cursor = col.find(
                {"agent_id": agent_id, "created_at": {"$gte": cutoff}},
                {"context": 1, "created_at": 1},
            )
            episodes = await cursor.to_list(length=5000)
        except Exception as e:
            logger.warning("regressive.get_trend failed: %s", e)
            return []

        # Initialize buckets
        result = []
        for i in range(buckets):
            bucket_start = cutoff + (bucket_size * i)
            bucket_end = bucket_start + bucket_size
            result.append({
                "bucket_start": bucket_start.isoformat(),
                "bucket_end": bucket_end.isoformat(),
                "values": [],
            })

        # Assign episodes to buckets
        for ep in episodes:
            ts = ep.get("created_at")
            if not ts:
                continue
            ctx = ep.get("context", {})
            if isinstance(ctx, str):
                continue
            val = ctx.get(metric)
            if val is None:
                continue

            # Find bucket
            offset = (ts - cutoff).total_seconds()
            bucket_idx = min(int(offset / bucket_size.total_seconds()), buckets - 1)
            if 0 <= bucket_idx < buckets:
                result[bucket_idx]["values"].append(float(val))

        # Compute averages
        for bucket in result:
            vals = bucket.pop("values")
            bucket["count"] = len(vals)
            bucket["avg"] = round(sum(vals) / len(vals), 2) if vals else 0

        return result


# ── Helpers ──────────────────────────────────────────────────────────────────

def _stats(values: list[float]) -> dict:
    """Compute basic statistics for a list of numbers."""
    if not values:
        return {"avg": 0, "min": 0, "max": 0, "stddev": 0, "count": 0}
    n = len(values)
    avg = sum(values) / n
    variance = sum((x - avg) ** 2 for x in values) / n
    return {
        "avg": round(avg, 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "stddev": round(variance ** 0.5, 3),
        "count": n,
    }
