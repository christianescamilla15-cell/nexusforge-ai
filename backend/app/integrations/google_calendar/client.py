"""Google Calendar integration — read events, check availability."""
from datetime import datetime, timedelta, timezone
import httpx
from ..config import IntegrationConfig
from ..google_drive.client import _get_access_token

async def list_events(days_ahead: int = 7, max_results: int = 10) -> dict:
    """List upcoming calendar events."""
    if not IntegrationConfig.GOOGLE_CREDENTIALS_PATH and not IntegrationConfig.GOOGLE_CREDENTIALS_JSON:
        return {"status": "not_configured", "events": []}

    try:
        token = await _get_access_token()
        if not token:
            return {"status": "auth_failed", "events": []}

        now = datetime.now(tz=timezone.utc)
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"
        calendar_id = IntegrationConfig.CALENDAR_ID or "primary"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "maxResults": max_results,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

        events = [{
            "id": e.get("id"),
            "summary": e.get("summary", "No title"),
            "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
            "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date", "")),
            "status": e.get("status", "confirmed"),
        } for e in items]

        return {"status": "success", "events": events, "total": len(events)}
    except Exception as e:
        return {"status": "error", "events": [], "message": str(e)}

async def get_availability(date: str = None) -> dict:
    """Check available time slots for a specific date."""
    if not date:
        date = (datetime.now(tz=timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")

    events = await list_events(days_ahead=7)
    if events["status"] != "success":
        return events

    busy_slots = []
    for e in events["events"]:
        if date in e.get("start", ""):
            busy_slots.append({"start": e["start"], "end": e["end"], "summary": e["summary"]})

    # Generate available slots (9am-5pm, 1-hour blocks)
    all_slots = [f"{date}T{h:02d}:00:00" for h in range(9, 17)]
    available = [s for s in all_slots if not any(s in b["start"] for b in busy_slots)]

    return {"status": "success", "date": date, "busy": busy_slots, "available": available}
