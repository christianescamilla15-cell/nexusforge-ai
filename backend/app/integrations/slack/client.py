"""Slack integration — send workflow notifications to Slack channels."""

import json
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...auth.jwt_handler import verify_token
from ...db.client import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations/slack", tags=["Slack"])


async def notify_slack(
    user_id: str,
    event_type: str,
    workflow_name: str,
    status: str,
    tokens: int = 0,
    cost: float = 0.0,
    agents_used: list = None,
    summary: str = "",
) -> bool:
    """Send notification to all active Slack webhooks for the user."""
    try:
        pool = await get_db_pool()
        if not pool:
            return False

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT webhook_url, channel_name FROM slack_integrations
                   WHERE user_id = $1::uuid AND is_active = true AND $2 = ANY(notify_on)""",
                user_id, event_type,
            )

        if not rows:
            return False

        status_emoji = "✅" if status == "completed" else "❌" if status == "failed" else "⏳"
        agents_text = ", ".join(agents_used[:5]) if agents_used else "N/A"

        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"{status_emoji} NexusForge: {workflow_name}"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Status:*\n{status.upper()}"},
                        {"type": "mrkdwn", "text": f"*Tokens:*\n{tokens:,}"},
                        {"type": "mrkdwn", "text": f"*Cost:*\n${cost:.4f}"},
                        {"type": "mrkdwn", "text": f"*Agents:*\n{agents_text}"},
                    ]
                },
            ]
        }

        if summary:
            payload["blocks"].append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary:*\n{summary[:300]}"}
            })

        sent = 0
        async with httpx.AsyncClient(timeout=5.0) as client:
            for row in rows:
                try:
                    resp = await client.post(row["webhook_url"], json=payload)
                    if resp.status_code == 200:
                        sent += 1
                except Exception:
                    pass

        logger.info("Slack notified %d/%d channels for %s", sent, len(rows), workflow_name)
        return sent > 0

    except Exception as e:
        logger.warning("Slack notification failed: %s", e)
        return False


class SlackWebhookRequest(BaseModel):
    webhook_url: str
    channel_name: Optional[str] = None
    notify_on: list[str] = ["workflow.completed", "workflow.failed"]


@router.post("/connect")
async def connect_slack(req: SlackWebhookRequest, request: Request):
    """Add a Slack webhook for notifications."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    # Validate webhook URL
    if not req.webhook_url.startswith("https://hooks.slack.com/"):
        raise HTTPException(400, "Invalid Slack webhook URL")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO slack_integrations (user_id, webhook_url, channel_name, notify_on)
               VALUES ($1::uuid, $2, $3, $4)""",
            token_data["sub"], req.webhook_url, req.channel_name, req.notify_on,
        )

    return {"connected": True, "channel": req.channel_name}


@router.get("/")
async def list_integrations(request: Request):
    """List Slack integrations."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, channel_name, notify_on, is_active, created_at
               FROM slack_integrations WHERE user_id = $1::uuid ORDER BY created_at DESC""",
            token_data["sub"],
        )

    return {
        "integrations": [{
            "id": str(r["id"]),
            "channel": r["channel_name"],
            "notify_on": r["notify_on"],
            "active": r["is_active"],
        } for r in rows]
    }


@router.delete("/{integration_id}")
async def disconnect_slack(integration_id: str, request: Request):
    """Remove a Slack integration."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM slack_integrations WHERE id = $1::uuid AND user_id = $2::uuid",
            integration_id, token_data["sub"],
        )

    return {"disconnected": True}
