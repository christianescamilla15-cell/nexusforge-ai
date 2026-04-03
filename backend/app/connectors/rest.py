"""Generic REST API connector — configurable HTTP client."""
import json
import logging

import httpx

from .base import ConnectorBase, ConnectorResult

logger = logging.getLogger(__name__)


class RestConnector(ConnectorBase):
    connector_type = "rest"
    name = "REST API"
    description = "Generic connector for any REST API — configurable base URL, headers, and methods"
    icon = "🌐"
    config_schema = {
        "fields": [
            {"key": "base_url", "label": "Base URL", "type": "text",
             "placeholder": "https://api.example.com/v1", "required": True},
            {"key": "headers", "label": "Default Headers (JSON)", "type": "textarea",
             "placeholder": '{"Authorization": "Bearer ...", "Content-Type": "application/json"}',
             "required": False},
            {"key": "auth_type", "label": "Auth Type", "type": "select",
             "options": ["none", "bearer", "api_key", "basic"], "required": False},
            {"key": "auth_value", "label": "Auth Value (token, key, or user:pass)", "type": "password",
             "placeholder": "your-token-or-key", "required": False},
            {"key": "timeout", "label": "Timeout (seconds)", "type": "number",
             "placeholder": "30", "required": False},
        ]
    }

    def _build_headers(self, config: dict) -> dict:
        headers = {"Content-Type": "application/json"}

        # Parse custom headers
        raw = config.get("headers", "")
        if raw and isinstance(raw, str):
            try:
                headers.update(json.loads(raw))
            except json.JSONDecodeError:
                pass
        elif isinstance(raw, dict):
            headers.update(raw)

        # Apply auth
        auth_type = config.get("auth_type", "none")
        auth_value = config.get("auth_value", "")
        if auth_type == "bearer" and auth_value:
            headers["Authorization"] = f"Bearer {auth_value}"
        elif auth_type == "api_key" and auth_value:
            headers["X-API-Key"] = auth_value
        elif auth_type == "basic" and auth_value:
            import base64
            encoded = base64.b64encode(auth_value.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        return headers

    async def test_connection(self, config: dict) -> dict:
        base_url = config.get("base_url", "")
        if not base_url or not base_url.startswith("http"):
            return {"ok": False, "message": "Invalid base_url — must start with http:// or https://"}

        timeout = int(config.get("timeout", 30))
        headers = self._build_headers(config)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(base_url, headers=headers)
                return {
                    "ok": resp.status_code < 500,
                    "message": f"GET {base_url} returned {resp.status_code} ({len(resp.content)} bytes)",
                }
        except httpx.ConnectError:
            return {"ok": False, "message": f"Could not connect to {base_url}"}
        except Exception as e:
            return {"ok": False, "message": f"Connection test failed: {str(e)[:200]}"}

    async def fetch(self, config: dict, params: dict = None) -> dict:
        params = params or {}
        base_url = config.get("base_url", "")
        path = params.get("path", "")
        method = params.get("method", "GET").upper()
        query = params.get("query_params", {})
        body = params.get("body")
        timeout = int(config.get("timeout", 30))

        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}" if path else base_url
        headers = self._build_headers(config)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(method, url, headers=headers, params=query, json=body)
                try:
                    data = resp.json()
                except Exception:
                    data = {"raw": resp.text[:5000]}

                count = 0
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    # Try common pagination patterns
                    for key in ("results", "data", "items", "records"):
                        if key in data and isinstance(data[key], list):
                            count = len(data[key])
                            break

                return ConnectorResult(
                    status="success" if resp.status_code < 400 else "error",
                    data={"status_code": resp.status_code, "response": data, "url": url},
                    error=None if resp.status_code < 400 else f"HTTP {resp.status_code}",
                    count=count,
                ).to_dict()
        except Exception as e:
            return ConnectorResult(
                status="error",
                error=f"Request failed: {str(e)[:300]}",
                data={"url": url, "method": method},
            ).to_dict()

    async def push(self, config: dict, data: dict) -> dict:
        base_url = config.get("base_url", "")
        path = data.get("path", "")
        method = data.get("method", "POST").upper()
        body = data.get("body", {})
        timeout = int(config.get("timeout", 30))

        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}" if path else base_url
        headers = self._build_headers(config)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(method, url, headers=headers, json=body)
                try:
                    resp_data = resp.json()
                except Exception:
                    resp_data = {"raw": resp.text[:5000]}

                return ConnectorResult(
                    status="success" if resp.status_code < 400 else "error",
                    data={"status_code": resp.status_code, "response": resp_data, "url": url, "method": method},
                    error=None if resp.status_code < 400 else f"HTTP {resp.status_code}",
                ).to_dict()
        except Exception as e:
            return ConnectorResult(
                status="error",
                error=f"Request failed: {str(e)[:300]}",
                data={"url": url, "method": method},
            ).to_dict()
