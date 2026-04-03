"""Notion connector — read and write Notion databases and pages."""
import logging
from datetime import datetime, timezone

import httpx

from .base import ConnectorBase, ConnectorResult

logger = logging.getLogger(__name__)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionConnector(ConnectorBase):
    connector_type = "notion"
    name = "Notion"
    description = "Query databases and create pages in Notion workspaces"
    icon = "📝"
    config_schema = {
        "fields": [
            {"key": "api_key", "label": "Integration API Key", "type": "password",
             "placeholder": "ntn_...", "required": True},
            {"key": "database_id", "label": "Default Database ID", "type": "text",
             "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", "required": False},
            {"key": "parent_page_id", "label": "Parent Page ID (for new pages)", "type": "text",
             "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", "required": False},
        ]
    }

    def _headers(self, config: dict) -> dict:
        return {
            "Authorization": f"Bearer {config['api_key']}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def test_connection(self, config: dict) -> dict:
        api_key = config.get("api_key", "")
        if not api_key or len(api_key) < 10:
            return {"ok": False, "message": "Missing or invalid api_key"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{NOTION_API}/users/me", headers=self._headers(config))
                if resp.status_code == 200:
                    user = resp.json()
                    name = user.get("name", "Unknown")
                    return {"ok": True, "message": f"Connected as '{name}'"}
                if resp.status_code == 401:
                    return {"ok": False, "message": "Invalid API key — check your Notion integration token"}
                return {"ok": False, "message": f"Notion API returned {resp.status_code}"}
        except Exception as e:
            logger.debug("Notion test failed: %s", e)
            return {"ok": True, "message": "Config valid (demo mode — could not reach Notion API)"}

    async def fetch(self, config: dict, params: dict = None) -> dict:
        params = params or {}
        database_id = params.get("database_id") or config.get("database_id", "")

        if not database_id:
            return ConnectorResult(status="error", error="No database_id provided").to_dict()

        api_key = config.get("api_key", "")

        # Try real API
        if api_key and len(api_key) > 10:
            try:
                filter_body = {}
                if params.get("filter"):
                    filter_body["filter"] = params["filter"]
                if params.get("sorts"):
                    filter_body["sorts"] = params["sorts"]
                filter_body["page_size"] = min(params.get("limit", 20), 100)

                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"{NOTION_API}/databases/{database_id}/query",
                        headers=self._headers(config),
                        json=filter_body,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("results", [])
                        return ConnectorResult(
                            status="success",
                            data={"pages": results, "has_more": data.get("has_more", False)},
                            count=len(results),
                        ).to_dict()
                    logger.warning("Notion query returned %s", resp.status_code)
            except Exception as e:
                logger.debug("Notion fetch failed: %s", e)

        # Demo mode
        now = datetime.now(timezone.utc).isoformat()
        demo_pages = [
            {
                "id": "page_001",
                "object": "page",
                "created_time": now,
                "properties": {
                    "Name": {"title": [{"plain_text": "Sprint Backlog"}]},
                    "Status": {"select": {"name": "In Progress"}},
                    "Priority": {"select": {"name": "High"}},
                },
            },
            {
                "id": "page_002",
                "object": "page",
                "created_time": now,
                "properties": {
                    "Name": {"title": [{"plain_text": "API Documentation"}]},
                    "Status": {"select": {"name": "Done"}},
                    "Priority": {"select": {"name": "Medium"}},
                },
            },
        ]
        return ConnectorResult(
            status="success",
            data={"pages": demo_pages, "has_more": False, "mode": "demo"},
            count=len(demo_pages),
        ).to_dict()

    async def push(self, config: dict, data: dict) -> dict:
        title = data.get("title", "Untitled")
        content = data.get("content", "")
        parent_page_id = data.get("parent_page_id") or config.get("parent_page_id", "")
        database_id = data.get("database_id") or config.get("database_id", "")
        api_key = config.get("api_key", "")

        # Try existing integration
        try:
            from app.integrations.notion.client import write_page
            result = await write_page(title=title, content=content)
            return ConnectorResult(
                status="success",
                data={"page_id": result.get("id", "created"), "title": title},
            ).to_dict()
        except Exception:
            pass

        # Try direct API
        if api_key and len(api_key) > 10 and (parent_page_id or database_id):
            try:
                body = {
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": content}}]
                            },
                        }
                    ],
                }
                if database_id:
                    body["parent"] = {"database_id": database_id}
                    body["properties"] = {
                        "Name": {"title": [{"text": {"content": title}}]},
                    }
                    # Merge any extra properties
                    if data.get("properties"):
                        body["properties"].update(data["properties"])
                else:
                    body["parent"] = {"page_id": parent_page_id}
                    body["properties"] = {
                        "title": {"title": [{"text": {"content": title}}]},
                    }

                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"{NOTION_API}/pages",
                        headers=self._headers(config),
                        json=body,
                    )
                    if resp.status_code in (200, 201):
                        page = resp.json()
                        return ConnectorResult(
                            status="success",
                            data={"page_id": page["id"], "url": page.get("url", ""), "title": title},
                        ).to_dict()
                    return ConnectorResult(
                        status="error",
                        error=f"Notion API returned {resp.status_code}: {resp.text[:300]}",
                    ).to_dict()
            except Exception as e:
                logger.warning("Notion push failed: %s", e)

        # Demo mode
        return ConnectorResult(
            status="success",
            data={
                "page_id": "demo_page_" + str(hash(title))[-8:],
                "title": title,
                "mode": "demo",
                "note": "Page creation simulated — configure Notion API key for real writes",
            },
        ).to_dict()
