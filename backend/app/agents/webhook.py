"""WebhookAgent — real HTTP webhook delivery with retry and signing."""

import hmac
import hashlib
import json
import logging
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class WebhookDeliveryError(Exception):
    pass


class WebhookAgent(BaseAgent):
    name = "WebhookAgent"
    agent_type = "webhook"
    description = "Sends data to external systems via webhooks with HMAC signing and retry."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        url = input_data.get("url", input_data.get("text", ""))
        payload = input_data.get("payload", {"event": "task_complete", "status": "success"})
        secret = input_data.get("secret", config.get("webhook_secret")) if config else input_data.get("secret")
        config = config or {}

        if config.get("demo") or not url:
            return AgentResult(
                output={
                    "webhook_sent": True,
                    "response_status": 200,
                    "payload_size": len(json.dumps(payload)),
                    "latency_ms": 0,
                    "_delivery_method": "demo",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        # Build payload with timestamp
        delivery_payload = {
            **payload,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        payload_bytes = json.dumps(delivery_payload, sort_keys=True).encode()

        # HMAC-SHA256 signing
        headers = {"Content-Type": "application/json"}
        if secret:
            sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
            headers["X-NexusForge-Signature"] = f"sha256={sig}"

        # Real HTTP delivery with retry
        start = time.monotonic()
        try:
            status, success = await self._deliver(url, payload_bytes, headers)
            latency_ms = round((time.monotonic() - start) * 1000)

            return AgentResult(
                output={
                    "webhook_sent": success,
                    "response_status": status,
                    "payload_size": len(payload_bytes),
                    "latency_ms": latency_ms,
                    "url": url,
                    "_delivery_method": "real_http",
                    "_signed": bool(secret),
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="httpx",
            )
        except Exception as exc:
            latency_ms = round((time.monotonic() - start) * 1000)
            logger.warning("WebhookAgent delivery failed after retries: %s", exc)
            return AgentResult(
                output={
                    "webhook_sent": False,
                    "response_status": 0,
                    "payload_size": len(payload_bytes),
                    "latency_ms": latency_ms,
                    "url": url,
                    "error": str(exc),
                    "_delivery_method": "failed",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="httpx",
            )

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=2, max=30, jitter=3),
        retry=retry_if_exception_type((WebhookDeliveryError, httpx.ConnectError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _deliver(url: str, payload_bytes: bytes, headers: dict) -> tuple[int, bool]:
        """Deliver webhook with retry on transient failures."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, content=payload_bytes, headers=headers)
            if resp.status_code < 300:
                return resp.status_code, True
            if resp.status_code in _RETRYABLE_STATUS:
                raise WebhookDeliveryError(f"Retryable: {resp.status_code}")
            return resp.status_code, False


register_agent("webhook", WebhookAgent())
