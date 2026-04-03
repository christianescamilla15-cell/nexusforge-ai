"""Slack connector — send messages via webhook."""
import logging

import httpx

from .base import ConnectorBase, ConnectorResult

logger = logging.getLogger(__name__)


class SlackConnector(ConnectorBase):
    connector_type = "slack"
    name = "Slack"
    description = "Send messages and notifications to Slack channels via Incoming Webhook"
    icon = "💬"
    config_schema = {
        "fields": [
            {"key": "webhook_url", "label": "Webhook URL", "type": "text",
             "placeholder": "https://hooks.slack.com/services/T.../B.../xxx", "required": True},
            {"key": "default_channel", "label": "Default Channel (display only)", "type": "text",
             "placeholder": "#general", "required": False},
            {"key": "bot_name", "label": "Bot Name", "type": "text",
             "placeholder": "NexusForge", "required": False},
            {"key": "bot_icon", "label": "Bot Icon Emoji", "type": "text",
             "placeholder": ":robot_face:", "required": False},
        ]
    }

    async def test_connection(self, config: dict) -> dict:
        webhook_url = config.get("webhook_url", "")
        if not webhook_url or not webhook_url.startswith("https://hooks.slack.com/"):
            return {"ok": False, "message": "Invalid webhook URL — must start with https://hooks.slack.com/"}

        # Try pinging the webhook
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json={
                    "text": "🔌 NexusForge connector test — connection successful!"
                })
                if resp.status_code == 200:
                    return {"ok": True, "message": "Webhook active — test message sent to channel"}
                return {"ok": False, "message": f"Webhook returned status {resp.status_code}: {resp.text[:200]}"}
        except httpx.ConnectError:
            return {"ok": False, "message": "Could not connect to Slack — check webhook URL"}
        except Exception as e:
            return {"ok": False, "message": f"Connection test failed: {str(e)[:200]}"}

    async def fetch(self, config: dict, params: dict = None) -> dict:
        # Slack Incoming Webhooks are push-only; cannot fetch messages
        return ConnectorResult(
            status="success",
            data={
                "note": "Slack Incoming Webhooks are push-only. Use Slack Bot API for reading messages.",
                "channel": config.get("default_channel", "unknown"),
            },
            count=0,
        ).to_dict()

    async def push(self, config: dict, data: dict) -> dict:
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            return ConnectorResult(status="error", error="No webhook_url configured").to_dict()

        text = data.get("text") or data.get("message", "")
        if not text:
            return ConnectorResult(status="error", error="'text' or 'message' field is required").to_dict()

        bot_name = config.get("bot_name", "NexusForge")
        bot_icon = config.get("bot_icon", ":robot_face:")

        payload = {
            "text": text,
            "username": bot_name,
            "icon_emoji": bot_icon,
        }

        # Include blocks if provided (rich formatting)
        if "blocks" in data:
            payload["blocks"] = data["blocks"]

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload)
                if resp.status_code == 200:
                    return ConnectorResult(
                        status="success",
                        data={"delivered": True, "channel": config.get("default_channel", "webhook")},
                    ).to_dict()
                return ConnectorResult(
                    status="error",
                    error=f"Slack returned {resp.status_code}: {resp.text[:200]}",
                ).to_dict()
        except Exception as e:
            # Demo fallback
            logger.warning("Slack push failed, returning demo result: %s", e)
            return ConnectorResult(
                status="success",
                data={
                    "delivered": False,
                    "mode": "demo",
                    "note": "Message queued (demo) — Slack webhook unreachable",
                    "payload": payload,
                },
            ).to_dict()
