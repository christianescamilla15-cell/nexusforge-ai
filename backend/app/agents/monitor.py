"""MonitorAgent — statistical anomaly detection + LLM narrative."""

import json
import logging
import math

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

# In-memory adaptive thresholds (EMA baselines per metric)
_BASELINES: dict[str, dict] = {}
_EMA_ALPHA = 0.2  # smoothing factor

MONITOR_PROMPT = """Analyze these pipeline metrics. Pre-computed anomaly detection has flagged issues.
Provide a natural-language assessment and actionable recommendations.

Metrics summary:
{metrics_summary}

Detected anomalies:
{anomalies}

Respond ONLY with valid JSON (no markdown):
{{
  "status": "<healthy|degraded|critical>",
  "anomalies": [{{"metric": "<name>", "expected": "<value>", "actual": "<value>", "severity": "<high|medium|low>", "explanation": "<why this matters>"}}],
  "recommendations": ["<action1>"],
  "health_score": <0-100>,
  "trend": "<improving|stable|degrading>"
}}"""


def _update_baseline(metric_name: str, value: float) -> dict:
    """Update EMA baseline for a metric. Returns {mean, std, is_anomaly, deviation}."""
    if metric_name not in _BASELINES:
        _BASELINES[metric_name] = {"mean": value, "variance": 0.0, "count": 1}
        return {"mean": value, "std": 0.0, "is_anomaly": False, "deviation": 0.0}

    b = _BASELINES[metric_name]
    old_mean = b["mean"]
    b["mean"] = _EMA_ALPHA * value + (1 - _EMA_ALPHA) * old_mean
    b["variance"] = _EMA_ALPHA * (value - b["mean"]) ** 2 + (1 - _EMA_ALPHA) * b["variance"]
    b["count"] += 1

    std = math.sqrt(b["variance"]) if b["variance"] > 0 else 0.001
    deviation = abs(value - b["mean"]) / std if std > 0 else 0.0
    is_anomaly = deviation > 2.0 and b["count"] >= 5  # need enough data points

    return {"mean": round(b["mean"], 2), "std": round(std, 2), "is_anomaly": is_anomaly, "deviation": round(deviation, 2)}


def _analyze_metrics(metrics: dict | list) -> tuple[list[dict], dict, int]:
    """Statistical anomaly detection. Returns (anomalies, summary, health_score)."""
    if isinstance(metrics, list):
        # Flatten list of metric dicts
        flat = {}
        for m in metrics:
            if isinstance(m, dict):
                flat.update(m)
        metrics = flat

    if not isinstance(metrics, dict):
        return [], {}, 50

    anomalies = []
    summary = {}
    total_deviation = 0.0
    metric_count = 0

    for key, value in metrics.items():
        if not isinstance(value, (int, float)):
            continue

        baseline = _update_baseline(key, value)
        summary[key] = {"current": value, **baseline}
        metric_count += 1
        total_deviation += baseline["deviation"]

        if baseline["is_anomaly"]:
            severity = "high" if baseline["deviation"] > 3.0 else "medium"
            anomalies.append({
                "metric": key,
                "expected": str(baseline["mean"]),
                "actual": str(value),
                "severity": severity,
                "deviation_sigma": baseline["deviation"],
            })

    # Health score: 100 - (avg deviation * 20), clamped to 0-100
    if metric_count > 0:
        avg_dev = total_deviation / metric_count
        health = max(0, min(100, int(100 - avg_dev * 20)))
    else:
        health = 50

    return anomalies, summary, health


class MonitorAgent(BaseAgent):
    name = "MonitorAgent"
    agent_type = "monitor"
    description = "Statistical anomaly detection with adaptive EMA baselines + LLM narrative."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        metrics = input_data.get("metrics", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not metrics:
            return AgentResult(
                output={
                    "status": "healthy",
                    "anomalies": [
                        {"metric": "avg_latency_ms", "expected": "200", "actual": "450", "severity": "medium"},
                    ],
                    "recommendations": ["Consider scaling extraction workers"],
                    "health_score": 82,
                    "trend": "stable",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        # Parse metrics if string
        if isinstance(metrics, str):
            try:
                metrics = json.loads(metrics)
            except (json.JSONDecodeError, ValueError):
                pass

        # Layer 1: Statistical anomaly detection (instant, $0)
        anomalies, summary, health_score = _analyze_metrics(metrics)

        # If no anomalies and health is good, skip LLM
        if not anomalies and health_score >= 80:
            return AgentResult(
                output={
                    "status": "healthy",
                    "anomalies": [],
                    "recommendations": [],
                    "health_score": health_score,
                    "trend": "stable",
                    "_metrics_summary": summary,
                    "_monitoring_method": "statistical_only",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="adaptive-ema",
            )

        # Layer 2: LLM for narrative when anomalies detected
        metrics_text = "\n".join(f"- {k}: current={v['current']}, baseline={v['mean']}±{v['std']}" for k, v in summary.items())
        anomalies_text = json.dumps(anomalies, indent=2) if anomalies else "None detected"

        messages = [
            {"role": "system", "content": self._build_system_prompt("Analyze pipeline health and recommend actions.")},
            {"role": "user", "content": MONITOR_PROMPT.format(
                metrics_summary=metrics_text[:2000],
                anomalies=anomalies_text[:1000],
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.2, max_tokens=1024)
            parsed = json.loads(resp.text)
            # Override with our deterministic health score
            parsed["health_score"] = health_score
            parsed["_metrics_summary"] = summary
            parsed["_monitoring_method"] = "statistical+llm"
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("MonitorAgent LLM fallback: %s", exc)
            status = "critical" if health_score < 40 else ("degraded" if health_score < 70 else "healthy")
            return AgentResult(
                output={
                    "status": status,
                    "anomalies": anomalies,
                    "recommendations": [f"LLM unavailable for analysis: {exc}"],
                    "health_score": health_score,
                    "trend": "unknown",
                    "_metrics_summary": summary,
                    "_monitoring_method": "statistical_fallback",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="adaptive-ema",
            )


register_agent("monitor", MonitorAgent())
