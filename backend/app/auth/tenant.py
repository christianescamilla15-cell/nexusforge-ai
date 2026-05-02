"""Tenant middleware — extracts org_id from JWT and exposes it to routes.

Flow:
  1. AuthMiddleware validates JWT → sets request.state.user
  2. TenantMiddleware reads user.org_id → sets request.state.org_id
  3. Routes filter queries explicitly using request.state.org_id

DB-layer Row-Level Security via session variable (`SET LOCAL app.org_id`)
is NOT in effect. asyncpg checks out a fresh connection per query from
the shared pool, so a `SET LOCAL` here is bound to a connection that is
released before the route's DB call runs — making any RLS policy that
reads `current_setting('app.org_id')` fall back to the default. Routes
must enforce tenant scope at the application layer (via WHERE clauses
or explicit JOINs against organization_members).

To restore real DB-layer RLS, the DB layer needs a per-request pinned
connection: acquire in middleware, run `SET LOCAL` in a transaction,
attach to request.state.db_conn, and have routes use that connection
exclusively. Tracked as Tier 2 work in 2026-05-02 triangulation triage
(see session_2026_05_02_triangulation_findings memory).

Usage in routes:
  org_id = getattr(request.state, 'org_id', None)
"""

import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.client import get_db_pool

logger = logging.getLogger(__name__)

# One-shot logging guard so we don't spam the log on every request when
# org_id is set but RLS isn't actually being enforced.
_RLS_DEGRADED_WARNED = False


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve and expose org_id on request.state for application-layer
    tenant filtering. Does NOT enforce DB-layer RLS — see module docstring.
    """

    async def dispatch(self, request: Request, call_next):
        user = getattr(request.state, "user", None)
        org_id = None

        if user:
            org_id = user.get("org_id")
            if not org_id:
                org_id = await self._lookup_org(user.get("sub"))

        request.state.org_id = org_id

        global _RLS_DEGRADED_WARNED
        if org_id and not _RLS_DEGRADED_WARNED:
            _RLS_DEGRADED_WARNED = True
            logger.warning(
                "TenantMiddleware: org_id=%s resolved but DB-layer RLS via "
                "session variable is not enforced; routes must filter by "
                "org_id explicitly. See app/auth/tenant.py docstring.",
                org_id,
            )

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
