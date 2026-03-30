"""Integration management and testing endpoints."""
from fastapi import APIRouter
from ..integrations.config import IntegrationConfig

router = APIRouter(prefix="/integrations", tags=["Integrations"])

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
