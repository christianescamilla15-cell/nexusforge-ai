"""Integration configuration — reads env vars fresh on every call."""
import os


def _env(key, default=""):
    return os.environ.get(key, default).strip()


class IntegrationConfig:
    """All attributes are properties that read env vars fresh (not cached)."""

    def __init__(self):
        pass

    @property
    def GOOGLE_CREDENTIALS_PATH(self):
        return _env("GOOGLE_CREDENTIALS_PATH")

    @property
    def GOOGLE_CREDENTIALS_JSON(self):
        return _env("GOOGLE_CREDENTIALS_JSON")

    @property
    def GMAIL_USER(self):
        return _env("GMAIL_USER")

    @property
    def CALENDAR_ID(self):
        return _env("GOOGLE_CALENDAR_ID", "primary")

    @property
    def NOTION_API_KEY(self):
        return _env("NOTION_API_KEY")

    @property
    def NOTION_DATABASE_ID(self):
        return _env("NOTION_DATABASE_ID")

    @property
    def WEBHOOK_URL(self):
        return _env("NEXUSFORGE_WEBHOOK_URL")

    def status(self):
        google_creds = _env("GOOGLE_CREDENTIALS_PATH") or _env("GOOGLE_CREDENTIALS_JSON")
        return {
            "google_drive": {"configured": bool(google_creds), "type": "Google Drive"},
            "gmail": {"configured": bool(google_creds and _env("GMAIL_USER")), "type": "Gmail API"},
            "google_calendar": {"configured": bool(google_creds), "type": "Google Calendar"},
            "notion": {"configured": bool(_env("NOTION_API_KEY")), "type": "Notion API"},
            "webhooks": {"configured": bool(_env("NEXUSFORGE_WEBHOOK_URL")), "type": "Webhook"},
        }


# Singleton instance — all clients import this
IntegrationConfig = IntegrationConfig()
