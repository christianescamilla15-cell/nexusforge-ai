"""Webhook client — sends workflow results to client-configured URLs.

Uses HMAC-SHA256 for request signing (secure against length-extension attacks)
and tenacity for automatic retries with exponential backoff.
"""

import hmac
import hashlib
import logging
import json
import time
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

logger = logging.getLogger(__name__)

# Retryable HTTP status codes (transient server errors + rate limit)
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class WebhookDeliveryError(Exception):
    """Raised when webhook delivery fails with a retryable status."""
    pass


def _sign_payload(secret: str, payload_bytes: bytes) -> str:
    """HMAC-SHA256 signature (secure, not vulnerable to length-extension)."""
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=2, max=60, jitter=5),
    retry=retry_if_exception_type((WebhookDeliveryError, httpx.ConnectError, httpx.TimeoutException)),
    reraise=True,
)
async def send_webhook(
    url: str,
    workflow_name: str,
    status: str,
    run_id: str,
    agents_used: list[str],
    total_tokens: int = 0,
    cost_usd: float = 0.0,
    processing_time_ms: float = 0,
    output: Optional[dict] = None,
    secret: Optional[str] = None,
) -> bool:
    """POST workflow result to client webhook URL. Returns True on success.

    Retries up to 5 times with exponential backoff on transient failures.
    Uses HMAC-SHA256 for request signing when secret is provided.
    """
    if not url:
        return False

    payload = {
        "event": "workflow.completed",
        "workflow": workflow_name,
        "status": status,
        "run_id": run_id,
        "agents_used": agents_used,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "processing_time_ms": processing_time_ms,
        "output": output or {},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-NexusForge-Signature"] = f"sha256={_sign_payload(secret, payload_bytes)}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, content=payload_bytes, headers=headers)
            if resp.status_code < 300:
                logger.info("Webhook sent to %s: %d", url, resp.status_code)
                return True
            if resp.status_code in _RETRYABLE_STATUS:
                raise WebhookDeliveryError(f"Retryable status {resp.status_code} from {url}")
            logger.warning("Webhook failed %s: %d (non-retryable)", url, resp.status_code)
            return False
    except (WebhookDeliveryError, httpx.ConnectError, httpx.TimeoutException):
        raise  # let tenacity retry
    except Exception as e:
        logger.warning("Webhook error %s: %s", url, e)
        return False
