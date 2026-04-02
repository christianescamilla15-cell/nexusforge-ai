"""Webhook client — sends workflow results to client-configured URLs."""

import logging
import json
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


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
    """POST workflow result to client webhook URL. Returns True on success."""
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
    }

    headers = {"Content-Type": "application/json"}
    if secret:
        import hashlib
        signature = hashlib.sha256(f"{secret}{json.dumps(payload, sort_keys=True)}".encode()).hexdigest()
        headers["X-NexusForge-Signature"] = signature

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code < 300:
                logger.info("Webhook sent to %s: %d", url, resp.status_code)
                return True
            logger.warning("Webhook failed %s: %d", url, resp.status_code)
            return False
    except Exception as e:
        logger.warning("Webhook error %s: %s", url, e)
        return False
