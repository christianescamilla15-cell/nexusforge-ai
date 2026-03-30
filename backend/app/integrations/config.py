"""Integration configuration — reads from environment variables."""
import os

class IntegrationConfig:
    # Google (service account JSON path OR inline JSON for serverless)
    GOOGLE_CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "").strip()
    GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
    GOOGLE_TOKEN_PATH = os.environ.get("GOOGLE_TOKEN_PATH", "").strip()

    # Gmail
    GMAIL_USER = os.environ.get("GMAIL_USER", "").strip()

    # Google Calendar
    CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary").strip()

    # Notion
    NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "").strip()
    NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "").strip()

    # Webhooks
    WEBHOOK_URL = os.environ.get("NEXUSFORGE_WEBHOOK_URL", "").strip()

    @classmethod
    def status(cls):
        return {
            "google_drive": {"configured": bool(cls.GOOGLE_CREDENTIALS_PATH or cls.GOOGLE_CREDENTIALS_JSON), "type": "Google Drive"},
            "gmail": {"configured": bool((cls.GOOGLE_CREDENTIALS_PATH or cls.GOOGLE_CREDENTIALS_JSON) and cls.GMAIL_USER), "type": "Gmail API"},
            "google_calendar": {"configured": bool(cls.GOOGLE_CREDENTIALS_PATH or cls.GOOGLE_CREDENTIALS_JSON), "type": "Google Calendar"},
            "notion": {"configured": bool(cls.NOTION_API_KEY), "type": "Notion API"},
            "webhooks": {"configured": bool(cls.WEBHOOK_URL), "type": "Webhook"},
        }
