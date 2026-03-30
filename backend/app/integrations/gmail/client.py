"""Gmail integration — read messages, extract structured email context."""
import httpx
from ..config import IntegrationConfig
from ..google_drive.client import _get_access_token

async def list_messages(query: str = "is:unread", max_results: int = 5) -> dict:
    """List Gmail messages matching a query."""
    if not IntegrationConfig.GOOGLE_CREDENTIALS_PATH and not IntegrationConfig.GOOGLE_CREDENTIALS_JSON:
        return {"status": "not_configured", "messages": [], "message": "Set GOOGLE_CREDENTIALS_PATH"}

    try:
        token = await _get_access_token()
        if not token:
            return {"status": "auth_failed", "messages": []}

        user = IntegrationConfig.GMAIL_USER or "me"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/{user}/messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": query, "maxResults": max_results},
            )
            resp.raise_for_status()
            message_ids = resp.json().get("messages", [])

            # Fetch details for each message
            messages = []
            for msg_ref in message_ids[:max_results]:
                detail = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/{user}/messages/{msg_ref['id']}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                )
                if detail.status_code == 200:
                    data = detail.json()
                    headers = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
                    messages.append({
                        "id": data["id"],
                        "subject": headers.get("Subject", ""),
                        "from": headers.get("From", ""),
                        "date": headers.get("Date", ""),
                        "snippet": data.get("snippet", ""),
                    })

        return {"status": "success", "messages": messages, "total": len(messages)}
    except Exception as e:
        return {"status": "error", "messages": [], "message": str(e)}

async def get_message_content(message_id: str) -> dict:
    """Get the full content of a specific Gmail message."""
    if not IntegrationConfig.GOOGLE_CREDENTIALS_PATH and not IntegrationConfig.GOOGLE_CREDENTIALS_JSON:
        return {"status": "not_configured", "content": ""}

    try:
        token = await _get_access_token()
        user = IntegrationConfig.GMAIL_USER or "me"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/{user}/messages/{message_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"format": "full"},
            )
            resp.raise_for_status()
            data = resp.json()
            snippet = data.get("snippet", "")
            return {"status": "success", "content": snippet, "id": message_id}
    except Exception as e:
        return {"status": "error", "content": "", "message": str(e)}
