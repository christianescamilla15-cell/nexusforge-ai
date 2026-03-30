"""
Google Drive integration — list files, fetch metadata, read document content.
Uses Google API Python client with service account or OAuth credentials.
For personal use: service account JSON is simplest.
"""
import os
import json
import httpx
from ..config import IntegrationConfig

async def list_files(query: str = "", max_results: int = 10) -> dict:
    """List files from Google Drive. Requires Google credentials."""
    if not IntegrationConfig.GOOGLE_CREDENTIALS_PATH:
        return {"status": "not_configured", "files": [], "message": "Set GOOGLE_CREDENTIALS_PATH env var"}

    # For MVP: use REST API with service account token
    try:
        token = await _get_access_token()
        if not token:
            return {"status": "auth_failed", "files": [], "message": "Could not obtain access token"}

        params = {"pageSize": max_results, "fields": "files(id,name,mimeType,modifiedTime,size)"}
        if query:
            params["q"] = f"name contains '{query}' and trashed = false"
        else:
            params["q"] = "trashed = false"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        return {"status": "success", "files": data.get("files", []), "total": len(data.get("files", []))}
    except Exception as e:
        return {"status": "error", "files": [], "message": str(e)}

async def get_file_content(file_id: str) -> dict:
    """Fetch text content of a Google Drive document."""
    if not IntegrationConfig.GOOGLE_CREDENTIALS_PATH:
        return {"status": "not_configured", "content": "", "message": "Set GOOGLE_CREDENTIALS_PATH"}

    try:
        token = await _get_access_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to export as plain text (works for Docs, Sheets)
            resp = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}/export",
                headers={"Authorization": f"Bearer {token}"},
                params={"mimeType": "text/plain"},
            )
            if resp.status_code == 200:
                return {"status": "success", "content": resp.text, "file_id": file_id}

            # Fallback: download raw content
            resp = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"alt": "media"},
            )
            resp.raise_for_status()
            return {"status": "success", "content": resp.text[:50000], "file_id": file_id}
    except Exception as e:
        return {"status": "error", "content": "", "message": str(e)}

async def _get_access_token() -> str:
    """Get access token from service account credentials."""
    creds_path = IntegrationConfig.GOOGLE_CREDENTIALS_PATH
    if not creds_path or not os.path.exists(creds_path):
        return ""

    try:
        # Use google-auth if available, otherwise return empty
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        SCOPES = [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        creds.refresh(Request())
        return creds.token
    except ImportError:
        return ""  # google-auth not installed
    except Exception:
        return ""
