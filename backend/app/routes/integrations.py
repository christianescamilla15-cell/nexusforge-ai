"""Integration management — user keys, service config, and testing endpoints."""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ..integrations.config import IntegrationConfig
from ..auth.jwt_handler import verify_token
from ..db.client import get_db_pool
from ..llm.user_provider import AVAILABLE_PROVIDERS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["Integrations"])

AVAILABLE_SERVICES = [
    {"id": "email", "name": "Email (Resend)", "icon": "mail", "category": "output",
     "fields": [{"key": "resend_api_key", "label": "Resend API Key", "type": "password", "placeholder": "re_..."}]},
    {"id": "notion", "name": "Notion", "icon": "edit", "category": "output",
     "fields": [{"key": "notion_api_key", "label": "API Key", "type": "password", "placeholder": "ntn_..."},
                {"key": "database_id", "label": "Database ID", "type": "text"}]},
    {"id": "slack", "name": "Slack", "icon": "message-circle", "category": "output",
     "fields": [{"key": "webhook_url", "label": "Webhook URL", "type": "text", "placeholder": "https://hooks.slack.com/..."}]},
    {"id": "webhook", "name": "Custom Webhook", "icon": "link", "category": "output",
     "fields": [{"key": "url", "label": "URL", "type": "text"}, {"key": "secret", "label": "Secret", "type": "password"}]},
    {"id": "whatsapp", "name": "WhatsApp", "icon": "phone", "category": "output",
     "fields": [{"key": "twilio_sid", "label": "Twilio SID", "type": "password"},
                {"key": "twilio_token", "label": "Token", "type": "password"},
                {"key": "from_number", "label": "From", "type": "text"}]},
    {"id": "drive", "name": "Google Drive", "icon": "folder", "category": "input",
     "fields": [{"key": "credentials_json", "label": "Service Account JSON", "type": "textarea"}]},
    {"id": "gmail", "name": "Gmail", "icon": "inbox", "category": "input",
     "fields": [{"key": "credentials_json", "label": "OAuth JSON", "type": "textarea"}]},
    {"id": "calendar", "name": "Google Calendar", "icon": "calendar", "category": "input",
     "fields": [{"key": "credentials_json", "label": "Service Account JSON", "type": "textarea"},
                {"key": "calendar_id", "label": "Calendar ID", "type": "text"}]},
]


def _get_user_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")
    return token_data["sub"]

@router.get("/status")
async def integration_status():
    """Show status of all configured integrations."""
    return IntegrationConfig.status()

@router.get("/drive/files")
async def drive_list_files(query: str = "", limit: int = 10):
    from ..integrations.google_drive.client import list_files
    return await list_files(query=query, max_results=limit)

@router.get("/gmail/messages")
async def gmail_list_messages(query: str = "is:unread", limit: int = 5):
    from ..integrations.gmail.client import list_messages
    return await list_messages(query=query, max_results=limit)

@router.get("/calendar/events")
async def calendar_list_events(days: int = 7, limit: int = 10):
    from ..integrations.google_calendar.client import list_events
    return await list_events(days_ahead=days, max_results=limit)

@router.get("/calendar/availability")
async def calendar_availability(date: str = None):
    from ..integrations.google_calendar.client import get_availability
    return await get_availability(date=date)

@router.post("/notion/write")
async def notion_write(title: str, content: str):
    from ..integrations.notion.client import write_page
    return await write_page(title=title, content=content)

@router.get("/notion/query")
async def notion_query():
    from ..integrations.notion.client import query_database
    return await query_database()

@router.post("/webhook/send")
async def webhook_send(event_type: str, payload: dict):
    from ..integrations.webhooks.client import send_webhook
    return await send_webhook(event_type=event_type, payload=payload)


# ── LLM Providers ────────────────────────────────────────────────────────────

@router.get("/providers")
async def list_providers():
    """List available LLM providers with pricing."""
    return {"providers": AVAILABLE_PROVIDERS}


class SaveKeyRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None


@router.post("/providers/keys")
async def save_provider_key(req: SaveKeyRequest, request: Request):
    """Save user's LLM provider API key."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO user_provider_keys (user_id, provider, api_key_encrypted, model)
               VALUES ($1::uuid, $2, $3, $4)
               ON CONFLICT (user_id, provider) DO UPDATE SET api_key_encrypted = $3, model = $4""",
            user_id, req.provider, req.api_key, req.model,
        )
    return {"saved": True, "provider": req.provider}


@router.get("/providers/keys")
async def list_provider_keys(request: Request):
    """List user's LLM keys (masked)."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT provider, model, is_active, LEFT(api_key_encrypted, 8) || '...' as preview FROM user_provider_keys WHERE user_id = $1::uuid",
            user_id,
        )
    return {"keys": [dict(r) for r in rows]}


@router.delete("/providers/keys/{provider}")
async def delete_provider_key(provider: str, request: Request):
    user_id = _get_user_id(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_provider_keys WHERE user_id = $1::uuid AND provider = $2", user_id, provider)
    return {"deleted": True}


# ── Service Integrations ─────────────────────────────────────────────────────

@router.get("/services")
async def list_services():
    """List all available integrations."""
    return {"services": AVAILABLE_SERVICES}


class ConfigureRequest(BaseModel):
    service: str
    config: dict


@router.post("/services/configure")
async def configure_service(req: ConfigureRequest, request: Request):
    """Save integration config."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO user_integrations (user_id, service, config)
               VALUES ($1::uuid, $2, $3::jsonb)
               ON CONFLICT (user_id, service) DO UPDATE SET config = $3::jsonb, is_active = true""",
            user_id, req.service, json.dumps(req.config),
        )
    return {"saved": True, "service": req.service}


@router.get("/services/configured")
async def list_configured(request: Request):
    """List user's configured integrations."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT service, is_active, test_status FROM user_integrations WHERE user_id = $1::uuid",
            user_id,
        )
    configured = {r["service"]: r for r in rows}
    result = []
    for svc in AVAILABLE_SERVICES:
        r = configured.get(svc["id"])
        result.append({**svc, "configured": r is not None, "active": r["is_active"] if r else False,
                       "test_status": r["test_status"] if r else "untested"})
    return {"services": result}


@router.delete("/services/{service}")
async def remove_service(service: str, request: Request):
    user_id = _get_user_id(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM user_integrations WHERE user_id = $1::uuid AND service = $2", user_id, service)
    return {"deleted": True}
