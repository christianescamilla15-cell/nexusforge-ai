"""MonitorAgent — monitors pipeline health and detects anomalies."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

MONITOR_PROMPT = """Analyze the following pipeline execution metrics for anomalies and health issues.

Respond ONLY with valid JSON (no markdown):
{{"status": "<healthy/degraded/critical>", "anomalies": [{{"metric": "<name>", "expected": "<value>", "actual": "<value>", "severity": "<high/medium/low>"}}], "recommendations": ["<action1>"], "health_score": <0-100>}}

Metrics:
{metrics}"""


class MonitorAgent(BaseAgent):
    name = "MonitorAgent"
    agent_type = "monitor"
    description = "Monitors pipeline health metrics and analyzes execution patterns for anomalies."

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
                    "recommendations": [
                        "Consider scaling extraction workers",
                        "Review LLM provider latency spikes",
                    ],
                    "health_score": 82,
                },
                provider="local", model="none",
            )

        raw = json.dumps(metrics) if isinstance(metrics, (dict, list)) else str(metrics)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Analyze pipeline health.")},
            {"role": "user", "content": MONITOR_PROMPT.format(metrics=raw[:3000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("MonitorAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"status": "unknown", "anomalies": [], "recommendations": [], "health_score": 0},
                provider="local", model="fallback",
            )


register_agent("monitor", MonitorAgent())
