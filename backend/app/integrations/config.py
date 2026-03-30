"""Integration configuration — reads from environment variables."""
import os

class IntegrationConfig:
    # Google (service account JSON path or OAuth)
    GOOGLE_CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    GOOGLE_TOKEN_PATH = os.environ.get("GOOGLE_TOKEN_PATH", "")

    # Gmail
    GMAIL_USER = os.environ.get("GMAIL_USER", "")

    # Google Calendar
    CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

    # Notion
    NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "").strip()
    NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

    # Webhooks
    WEBHOOK_URL = os.environ.get("NEXUSFORGE_WEBHOOK_URL", "")

    @classmethod
    def status(cls):
        return {
            "google_drive": {"configured": bool(cls.GOOGLE_CREDENTIALS_PATH), "type": "Google Drive"},
            "gmail": {"configured": bool(cls.GOOGLE_CREDENTIALS_PATH and cls.GMAIL_USER), "type": "Gmail API"},
            "google_calendar": {"configured": bool(cls.GOOGLE_CREDENTIALS_PATH), "type": "Google Calendar"},
            "notion": {"configured": bool(cls.NOTION_API_KEY), "type": "Notion API"},
            "webhooks": {"configured": bool(cls.WEBHOOK_URL), "type": "Webhook"},
        }
