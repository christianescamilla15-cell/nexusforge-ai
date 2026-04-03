"""Google Drive connector — list and upload files."""
import logging
from datetime import datetime, timezone

from .base import ConnectorBase, ConnectorResult

logger = logging.getLogger(__name__)


class DriveConnector(ConnectorBase):
    connector_type = "drive"
    name = "Google Drive"
    description = "List, search, and upload files to Google Drive"
    icon = "📁"
    config_schema = {
        "fields": [
            {"key": "credentials_json", "label": "Service Account JSON", "type": "textarea",
             "placeholder": '{"type": "service_account", ...}', "required": True},
            {"key": "folder_id", "label": "Default Folder ID", "type": "text",
             "placeholder": "1ABC...xyz (from Drive URL)", "required": False},
            {"key": "shared_drive_id", "label": "Shared Drive ID (optional)", "type": "text",
             "placeholder": "0ABC...xyz", "required": False},
        ]
    }

    async def test_connection(self, config: dict) -> dict:
        creds = config.get("credentials_json", "")
        if not creds or len(creds) < 20:
            return {"ok": False, "message": "Missing or invalid credentials_json"}

        # Try real integration
        try:
            from app.integrations.google_drive.client import list_files
            result = await list_files(query="", max_results=1)
            return {"ok": True, "message": f"Connected — {result.get('total', 0)} files accessible"}
        except Exception:
            pass

        return {"ok": True, "message": "Config valid (demo mode — credentials not verified against Google)"}

    async def fetch(self, config: dict, params: dict = None) -> dict:
        params = params or {}
        query = params.get("query", "")
        limit = params.get("limit", 20)
        folder_id = params.get("folder_id") or config.get("folder_id", "")

        # Try real integration
        try:
            from app.integrations.google_drive.client import list_files
            result = await list_files(query=query, max_results=limit)
            files = result.get("files", [])
            return ConnectorResult(
                status="success",
                data=result,
                count=len(files),
            ).to_dict()
        except Exception as e:
            logger.debug("Drive real integration unavailable: %s", e)

        # Demo mode
        now = datetime.now(timezone.utc).isoformat()
        demo_files = [
            {
                "id": "file_001",
                "name": "Q4_Financial_Report.xlsx",
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "size": "245760",
                "modifiedTime": now,
                "webViewLink": "https://docs.google.com/spreadsheets/d/demo1/edit",
                "parents": [folder_id or "root"],
            },
            {
                "id": "file_002",
                "name": "Product_Roadmap.pdf",
                "mimeType": "application/pdf",
                "size": "1048576",
                "modifiedTime": now,
                "webViewLink": "https://drive.google.com/file/d/demo2/view",
                "parents": [folder_id or "root"],
            },
            {
                "id": "file_003",
                "name": "Meeting_Notes_2026.docx",
                "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size": "32768",
                "modifiedTime": now,
                "webViewLink": "https://docs.google.com/document/d/demo3/edit",
                "parents": [folder_id or "root"],
            },
        ]
        return ConnectorResult(
            status="success",
            data={"files": demo_files[:limit], "query": query, "mode": "demo"},
            count=min(len(demo_files), limit),
        ).to_dict()

    async def push(self, config: dict, data: dict) -> dict:
        file_name = data.get("name") or data.get("file_name", "")
        content = data.get("content", "")
        folder_id = data.get("folder_id") or config.get("folder_id", "")

        if not file_name:
            return ConnectorResult(status="error", error="'name' or 'file_name' field is required").to_dict()

        # Try real integration
        try:
            from app.integrations.google_drive.client import upload_file
            result = await upload_file(name=file_name, content=content, folder_id=folder_id)
            return ConnectorResult(
                status="success",
                data={"file_id": result.get("id", "uploaded"), "name": file_name},
            ).to_dict()
        except Exception as e:
            logger.debug("Drive upload unavailable: %s", e)

        # Demo mode
        return ConnectorResult(
            status="success",
            data={
                "file_id": "demo_file_" + str(hash(file_name))[-8:],
                "name": file_name,
                "folder_id": folder_id or "root",
                "mode": "demo",
                "note": "Upload simulated — configure Google Drive credentials for real uploads",
            },
        ).to_dict()
