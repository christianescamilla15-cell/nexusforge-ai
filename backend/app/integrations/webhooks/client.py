"""Webhook integration — send structured workflow outputs to external endpoints."""
import httpx
from datetime import datetime
from ..config import IntegrationConfig

async def send_webhook(event_type: str, payload: dict, url: str = None) -> dict:
    """Send a webhook notification with workflow results."""
    target_url = url or IntegrationConfig.WEBHOOK_URL
    if not target_url:
        return {"status": "not_configured", "message": "Set NEXUSFORGE_WEBHOOK_URL or pass url parameter"}

    try:
        webhook_data = {
            "source": "nexusforge",
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(target_url, json=webhook_data)
            resp.raise_for_status()

        return {"status": "success", "url": target_url, "status_code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}
