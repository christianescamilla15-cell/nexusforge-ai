"""Notion integration — write structured outputs/results to a Notion database."""
import httpx
from ..config import IntegrationConfig

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

async def write_page(title: str, content: str, properties: dict = None) -> dict:
    """Create a new page in the configured Notion database."""
    if not IntegrationConfig.NOTION_API_KEY:
        return {"status": "not_configured", "message": "Set NOTION_API_KEY env var"}
    if not IntegrationConfig.NOTION_DATABASE_ID:
        return {"status": "not_configured", "message": "Set NOTION_DATABASE_ID env var"}

    try:
        headers = {
            "Authorization": f"Bearer {IntegrationConfig.NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

        page_data = {
            "parent": {"database_id": IntegrationConfig.NOTION_DATABASE_ID},
            "properties": {
                "Name": {"title": [{"text": {"content": title}}]},
                **(properties or {}),
            },
            "children": [
                {"object": "block", "type": "paragraph", "paragraph": {
                    "rich_text": [{"text": {"content": content[:2000]}}]
                }},
            ],
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{NOTION_API}/pages", headers=headers, json=page_data)
            resp.raise_for_status()
            data = resp.json()

        return {"status": "success", "page_id": data.get("id"), "url": data.get("url")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def query_database(filter_obj: dict = None) -> dict:
    """Query the configured Notion database."""
    if not IntegrationConfig.NOTION_API_KEY or not IntegrationConfig.NOTION_DATABASE_ID:
        return {"status": "not_configured", "results": []}

    try:
        headers = {
            "Authorization": f"Bearer {IntegrationConfig.NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

        body = {}
        if filter_obj:
            body["filter"] = filter_obj

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{NOTION_API}/databases/{IntegrationConfig.NOTION_DATABASE_ID}/query",
                headers=headers, json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        results = [{
            "id": r["id"],
            "title": r.get("properties", {}).get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "") if r.get("properties", {}).get("Name", {}).get("title") else "",
            "created": r.get("created_time"),
        } for r in data.get("results", [])]

        return {"status": "success", "results": results, "total": len(results)}
    except Exception as e:
        return {"status": "error", "results": [], "message": str(e)}
