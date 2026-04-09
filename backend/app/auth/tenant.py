"""Tenant middleware — extracts org_id from JWT and sets PostgreSQL session variable for RLS.

Flow:
  1. AuthMiddleware validates JWT → sets request.state.user
  2. TenantMiddleware reads user.org_id → sets PostgreSQL session var
  3. All DB queries automatically filtered by RLS policies
  4. If no org_id → user sees only their own data (backward compat)

Usage in routes:
  org_id = getattr(request.state, 'org_id', None)
"""

import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.client import get_db_pool

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Set PostgreSQL session variable for Row-Level Security."""

    async def dispatch(self, request: Request, call_next):
        # Extract org_id from authenticated user
        user = getattr(request.state, "user", None)
        org_id = None

        if user:
            org_id = user.get("org_id")
            # If user doesn't have org_id in JWT, look up from DB
            if not org_id:
                org_id = await self._lookup_org(user.get("sub"))

        request.state.org_id = org_id

        # Set PostgreSQL session variable for RLS
        if org_id:
            try:
                pool = await get_db_pool()
                async with pool.acquire() as conn:
                    await conn.execute(f"SET LOCAL app.org_id = '{org_id}'")
            except Exception:
                pass  # RLS will use fallback (org_id IS NULL)

        return await call_next(request)

    async def _lookup_org(self, user_id: str | None) -> str | None:
        """Look up user's primary organization from DB."""
        if not user_id:
            return None
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT om.org_id FROM organization_members om
                       WHERE om.user_id = $1::uuid
                       ORDER BY om.joined_at ASC LIMIT 1""",
                    user_id,
                )
                return str(row["org_id"]) if row else None
        except Exception:
            return None


async def get_user_org(request: Request) -> str | None:
    """Get the current user's org_id from request state."""
    return getattr(request.state, "org_id", None)


async def get_org_id_required(request: Request) -> str:
    """Get org_id or raise 403."""
    org_id = getattr(request.state, "org_id", None)
    if not org_id:
        from fastapi import HTTPException
        raise HTTPException(403, "Organization membership required")
    return org_id
