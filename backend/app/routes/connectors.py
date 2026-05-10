"""Connector Hub — CRUD and operations for universal external connectors."""
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth.jwt_handler import verify_token
from app.connectors.registry import get_connector, list_connector_types
from app.db.client import get_db_pool

router = APIRouter(prefix="/connectors", tags=["connectors"])
logger = logging.getLogger(__name__)

# Fields whose values should be masked in API responses
_SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "apikey", "access_key", "private_key"}


def _mask_config(cfg: dict) -> dict:
    """Return a copy of config with sensitive fields masked."""
    if not cfg or not isinstance(cfg, dict):
        return cfg
    masked = {}
    for k, v in cfg.items():
        if any(s in k.lower() for s in _SENSITIVE_KEYS) and v:
            masked[k] = "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
        else:
            masked[k] = v
    return masked


# ── Auth helper ──────────────────────────────────────────────────────────────

def _get_user_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")
    return token_data["sub"]


# ── Request models ───────────────────────────────────────────────────────────

class CreateConnectorRequest(BaseModel):
    connector_type: str
    name: str
    config: dict = {}
    field_mapping: dict = {}


class UpdateConnectorRequest(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None
    field_mapping: Optional[dict] = None
    is_active: Optional[bool] = None


class PushRequest(BaseModel):
    data: dict = {}


class FetchRequest(BaseModel):
    params: dict = {}


# ── Public endpoints ─────────────────────────────────────────────────────────

@router.get("/types")  # mythos: public — connector type catalog with schemas (no per-user data)
async def list_types():
    """List all available connector types with their config schemas."""
    return {"types": list_connector_types()}


# ── Authenticated endpoints ──────────────────────────────────────────────────

@router.get("/")
async def list_connectors(request: Request):
    """List all connectors for the authenticated user."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, connector_type, name, config, field_mapping,
                      is_active, last_test_at, last_test_status,
                      created_at, updated_at
               FROM connectors
               WHERE user_id = $1::uuid
               ORDER BY created_at DESC""",
            user_id,
        )
    connectors = []
    for r in rows:
        cfg = r["config"]
        if isinstance(cfg, str):
            cfg = json.loads(cfg)
        fm = r["field_mapping"]
        if isinstance(fm, str):
            fm = json.loads(fm)
        connectors.append({
            "id": str(r["id"]),
            "connector_type": r["connector_type"],
            "name": r["name"],
            "config": _mask_config(cfg),
            "field_mapping": fm,
            "is_active": r["is_active"],
            "last_test_at": r["last_test_at"].isoformat() if r["last_test_at"] else None,
            "last_test_status": r["last_test_status"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        })
    return {"connectors": connectors, "count": len(connectors)}


@router.post("/")
async def create_connector(body: CreateConnectorRequest, request: Request):
    """Create a new connector instance."""
    user_id = _get_user_id(request)

    # Validate connector type exists
    try:
        get_connector(body.connector_type)
    except KeyError:
        raise HTTPException(400, f"Unknown connector type: {body.connector_type}")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO connectors (user_id, connector_type, name, config, field_mapping)
               VALUES ($1::uuid, $2, $3, $4::jsonb, $5::jsonb)
               RETURNING id, created_at""",
            user_id,
            body.connector_type,
            body.name,
            json.dumps(body.config),
            json.dumps(body.field_mapping),
        )
    return {
        "id": str(row["id"]),
        "connector_type": body.connector_type,
        "name": body.name,
        "created_at": row["created_at"].isoformat(),
        "message": f"Connector '{body.name}' created",
    }


@router.put("/{connector_id}")
async def update_connector(connector_id: UUID, body: UpdateConnectorRequest, request: Request):
    """Update an existing connector's config, name, or status."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM connectors WHERE id = $1 AND user_id = $2::uuid",
            connector_id, user_id,
        )
        if not existing:
            raise HTTPException(404, "Connector not found")

        updates = []
        values = []
        idx = 1

        if body.name is not None:
            idx += 1
            updates.append(f"name = ${idx}")
            values.append(body.name)
        if body.config is not None:
            idx += 1
            updates.append(f"config = ${idx}::jsonb")
            values.append(json.dumps(body.config))
        if body.field_mapping is not None:
            idx += 1
            updates.append(f"field_mapping = ${idx}::jsonb")
            values.append(json.dumps(body.field_mapping))
        if body.is_active is not None:
            idx += 1
            updates.append(f"is_active = ${idx}")
            values.append(body.is_active)

        if not updates:
            raise HTTPException(400, "No fields to update")

        # Whitelist columns
        _ALLOWED = {"name", "config", "is_active"}
        updates = [u for u in updates if any(u.startswith(c) for c in _ALLOWED)]
        updates.append("updated_at = now()")
        set_clause = ", ".join(updates)
        await conn.execute(
            f"UPDATE connectors SET {set_clause} WHERE id = $1",
            connector_id, *values,
        )

    return {"id": str(connector_id), "updated": True}


@router.delete("/{connector_id}")
async def delete_connector(connector_id: UUID, request: Request):
    """Delete a connector."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM connectors WHERE id = $1 AND user_id = $2::uuid",
            connector_id, user_id,
        )
    if result == "DELETE 0":
        raise HTTPException(404, "Connector not found")
    return {"id": str(connector_id), "deleted": True}


@router.post("/{connector_id}/test")
async def test_connector(connector_id: UUID, request: Request):
    """Test a connector's connection with its stored config."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT connector_type, config FROM connectors WHERE id = $1 AND user_id = $2::uuid",
            connector_id, user_id,
        )
        if not row:
            raise HTTPException(404, "Connector not found")

        config = row["config"]
        if isinstance(config, str):
            config = json.loads(config)

        connector = get_connector(row["connector_type"])
        result = await connector.test_connection(config)

        status = "ok" if result.get("ok") else "failed"
        await conn.execute(
            "UPDATE connectors SET last_test_at = now(), last_test_status = $1 WHERE id = $2",
            status, connector_id,
        )

    return {"connector_id": str(connector_id), "test": result}


@router.post("/{connector_id}/fetch")
async def fetch_connector(connector_id: UUID, body: FetchRequest, request: Request):
    """Fetch data from a connector."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT connector_type, config, is_active
               FROM connectors WHERE id = $1 AND user_id = $2::uuid""",
            connector_id, user_id,
        )
    if not row:
        raise HTTPException(404, "Connector not found")
    if not row["is_active"]:
        raise HTTPException(400, "Connector is disabled")

    config = row["config"]
    if isinstance(config, str):
        config = json.loads(config)

    connector = get_connector(row["connector_type"])
    result = await connector.fetch(config, body.params)
    return {"connector_id": str(connector_id), "result": result}


@router.post("/{connector_id}/push")
async def push_connector(connector_id: UUID, body: PushRequest, request: Request):
    """Push data through a connector."""
    user_id = _get_user_id(request)
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT connector_type, config, is_active
               FROM connectors WHERE id = $1 AND user_id = $2::uuid""",
            connector_id, user_id,
        )
    if not row:
        raise HTTPException(404, "Connector not found")
    if not row["is_active"]:
        raise HTTPException(400, "Connector is disabled")

    config = row["config"]
    if isinstance(config, str):
        config = json.loads(config)

    connector = get_connector(row["connector_type"])
    result = await connector.push(config, body.data)
    return {"connector_id": str(connector_id), "result": result}
