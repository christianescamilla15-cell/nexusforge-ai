"""Gmail connector — read and send emails."""
import logging
from datetime import datetime, timezone

from .base import ConnectorBase, ConnectorResult

logger = logging.getLogger(__name__)


class GmailConnector(ConnectorBase):
    connector_type = "gmail"
    name = "Gmail"
    description = "Read inbox, search emails, and send messages via Gmail API"
    icon = "📧"
    config_schema = {
        "fields": [
            {"key": "credentials_json", "label": "OAuth Credentials JSON", "type": "textarea",
             "placeholder": '{"client_id": "...", "client_secret": "..."}', "required": True},
            {"key": "token_json", "label": "Token JSON (auto-populated after auth)", "type": "textarea",
             "placeholder": "Leave blank — filled after OAuth flow", "required": False},
            {"key": "default_from", "label": "Default From Address", "type": "text",
             "placeholder": "you@gmail.com", "required": False},
        ]
    }

    async def test_connection(self, config: dict) -> dict:
        creds = config.get("credentials_json", "")
        if not creds or len(creds) < 10:
            return {"ok": False, "message": "Missing or invalid credentials_json"}

        # Try real integration if available
        try:
            from app.integrations.gmail.client import list_messages
            result = await list_messages(query="is:unread", max_results=1)
            return {"ok": True, "message": f"Connected — found {len(result.get('messages', []))} unread messages"}
        except Exception:
            pass

        # Demo mode — validate config structure
        return {"ok": True, "message": "Config valid (demo mode — credentials not verified against Google)"}

    async def fetch(self, config: dict, params: dict = None) -> dict:
        params = params or {}
        query = params.get("query", "is:unread")
        limit = params.get("limit", 10)

        # Try real integration
        try:
            from app.integrations.gmail.client import list_messages
            result = await list_messages(query=query, max_results=limit)
            return ConnectorResult(
                status="success",
                data=result,
                count=len(result.get("messages", [])),
            ).to_dict()
        except Exception as e:
            logger.debug("Gmail real integration unavailable: %s", e)

        # Demo mode
        now = datetime.now(timezone.utc).isoformat()
        demo_emails = [
            {
                "id": "msg_001",
                "thread_id": "thread_001",
                "from": "alice@example.com",
                "to": config.get("default_from", "user@gmail.com"),
                "subject": "Q4 Report Review",
                "snippet": "Hi, please review the attached Q4 report by Friday...",
                "date": now,
                "labels": ["INBOX", "UNREAD"],
                "has_attachments": True,
            },
            {
                "id": "msg_002",
                "thread_id": "thread_002",
                "from": "bob@example.com",
                "to": config.get("default_from", "user@gmail.com"),
                "subject": "Meeting Tomorrow",
                "snippet": "Just confirming our 10am meeting tomorrow in room 3B...",
                "date": now,
                "labels": ["INBOX", "UNREAD"],
                "has_attachments": False,
            },
            {
                "id": "msg_003",
                "thread_id": "thread_003",
                "from": "noreply@github.com",
                "to": config.get("default_from", "user@gmail.com"),
                "subject": "[nexusforge] PR #42 merged",
                "snippet": "Your pull request has been merged into main...",
                "date": now,
                "labels": ["INBOX"],
                "has_attachments": False,
            },
        ]
        return ConnectorResult(
            status="success",
            data={"messages": demo_emails[:limit], "query": query, "mode": "demo"},
            count=min(len(demo_emails), limit),
        ).to_dict()

    async def push(self, config: dict, data: dict) -> dict:
        to = data.get("to")
        subject = data.get("subject", "(no subject)")
        body = data.get("body", "")

        if not to:
            return ConnectorResult(status="error", error="'to' field is required").to_dict()

        # Try real email integration (Resend)
        try:
            from app.integrations.email.client import send_email
            result = await send_email(to=to, subject=subject, html=body)
            return ConnectorResult(
                status="success",
                data={"message_id": result.get("id", "sent"), "to": to, "subject": subject},
            ).to_dict()
        except Exception as e:
            logger.debug("Email send unavailable: %s", e)

        # Demo mode
        return ConnectorResult(
            status="success",
            data={
                "message_id": "demo_msg_" + str(hash(to + subject))[-8:],
                "to": to,
                "subject": subject,
                "mode": "demo",
                "note": "Email simulated — configure Resend API key for real delivery",
            },
        ).to_dict()
