"""WebhookAgent — external system integration (simulated)."""

import json
import logging
import time
import random

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)


class WebhookAgent(BaseAgent):
    name = "WebhookAgent"
    agent_type = "webhook"
    description = "Sends data to external systems via webhooks and reports delivery status."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        url = input_data.get("url", input_data.get("text", "https://example.com/webhook"))
        payload = input_data.get("payload", {"event": "task_complete", "status": "success"})
        config = config or {}

        # Always simulated — no real HTTP calls to external systems
        payload_str = json.dumps(payload)
        latency = round(random.uniform(45, 320), 1)

        if config.get("demo") or not url:
            return AgentResult(
                output={
                    "webhook_sent": True,
                    "response_status": 200,
                    "payload_size": len(payload_str),
                    "latency_ms": latency,
                },
                provider="local", model="none",
            )

        # Simulate sending with realistic response
        success = random.random() > 0.05  # 95% success rate simulation
        status = 200 if success else 503

        return AgentResult(
            output={
                "webhook_sent": success,
                "response_status": status,
                "payload_size": len(payload_str),
                "latency_ms": latency,
            },
            provider="local", model="simulated",
        )


register_agent("webhook", WebhookAgent())
