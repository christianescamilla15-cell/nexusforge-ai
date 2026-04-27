"""Admin Panel API — super-admin management for NexusForge SaaS.

Protected: requires role='admin' in JWT token.
Returns 404 for non-admin users (no info leak).

Endpoints:
  GET    /admin/dashboard     — System health + KPIs
  GET    /admin/users         — List all users with usage
  GET    /admin/users/{id}    — User detail + history
  POST   /admin/users/{id}/suspend — Suspend user
  POST   /admin/users/{id}/activate — Reactivate user
  GET    /admin/orgs          — List all organizations
  GET    /admin/orgs/{id}     — Org detail + members + usage
  GET    /admin/usage         — Global usage analytics
  GET    /admin/audit         — Global audit log
  POST   /admin/announce      — Send announcement to all users
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.db.client import get_db_pool
from app.auth.jwt_handler import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(request: Request) -> dict:
    """Verify request is from an admin user. Returns 404 (not 403) to hide endpoint."""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(404, "Not found")
    return user


@router.get("/dashboard")
async def admin_dashboard(request: Request):
    """System health + KPIs for admin overview."""
    _require_admin(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Users
        users = await conn.fetchrow("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE is_active = true) AS active,
                   count(*) FILTER (WHERE created_at > now() - interval '7 days') AS new_7d,
                   count(*) FILTER (WHERE created_at > now() - interval '30 days') AS new_30d
            FROM nf_users
        """)

        # Organizations
        orgs = await conn.fetchrow("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE plan != 'free') AS paying
            FROM organizations
        """)

        # Runs
        runs = await conn.fetchrow("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE status = 'completed') AS completed,
                   count(*) FILTER (WHERE status = 'failed') AS failed,
                   count(*) FILTER (WHERE created_at > now() - interval '24 hours') AS last_24h,
                   COALESCE(SUM(total_tokens), 0) AS total_tokens,
                   COALESCE(SUM(total_cost_usd), 0) AS total_cost
            FROM workflow_runs
        """)

        # Automations
        automations = await conn.fetchrow("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE is_active = true) AS active
            FROM automations
        """)

        # Plan distribution
        plans = await conn.fetch("""
            SELECT COALESCE(plan, 'free') AS plan, count(*) AS users
            FROM nf_users GROUP BY plan ORDER BY users DESC
        """)

        # Recent errors
        recent_errors = await conn.fetch("""
            SELECT id, status, error_message, created_at
            FROM workflow_runs
            WHERE status = 'failed' AND created_at > now() - interval '24 hours'
            ORDER BY created_at DESC LIMIT 10
        """)

    return {
        "users": {
            "total": users["total"],
            "active": users["active"],
            "new_7d": users["new_7d"],
            "new_30d": users["new_30d"],
        },
        "organizations": {
            "total": orgs["total"] if orgs else 0,
            "paying": orgs["paying"] if orgs else 0,
        },
        "runs": {
            "total": runs["total"],
            "completed": runs["completed"],
            "failed": runs["failed"],
            "last_24h": runs["last_24h"],
            "total_tokens": int(runs["total_tokens"]),
            "total_cost_usd": round(float(runs["total_cost"]), 4),
        },
        "automations": {
            "total": automations["total"],
            "active": automations["active"],
        },
        "plans": {p["plan"]: p["users"] for p in plans},
        "recent_errors": [
            {
                "id": str(e["id"]),
                "error": (e["error_message"] or "")[:100],
                "created_at": e["created_at"].isoformat(),
            }
            for e in recent_errors
        ],
    }


@router.get("/users")
async def list_users(
    request: Request,
    search: str = Query("", description="Search by email or name"),
    plan: str = Query("", description="Filter by plan"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List all users with usage stats."""
    _require_admin(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        conditions = []
        params = []
        idx = 1

        if search:
            conditions.append(f"(u.email ILIKE ${idx} OR u.name ILIKE ${idx})")
            params.append(f"%{search}%")
            idx += 1

        if plan:
            conditions.append(f"u.plan = ${idx}")
            params.append(plan)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        params.extend([limit, skip])
        rows = await conn.fetch(f"""
            SELECT u.id, u.email, u.name, u.plan, u.is_active, u.created_at,
                   u.runs_today, u.email_verified,
                   COALESCE(s.total_runs, 0) AS total_runs,
                   COALESCE(s.total_tokens, 0) AS total_tokens,
                   COALESCE(s.total_cost, 0) AS total_cost
            FROM nf_users u
            LEFT JOIN user_execution_stats s ON s.user_id = u.id
            {where}
            ORDER BY u.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """, *params)

        total = await conn.fetchval(f"SELECT count(*) FROM nf_users u {where}", *params[:-2])

    return {
        "total": total,
        "users": [
            {
                "id": str(r["id"]),
                "email": r["email"],
                "name": r["name"],
                "plan": r["plan"] or "free",
                "is_active": r["is_active"],
                "email_verified": r["email_verified"],
                "created_at": r["created_at"].isoformat(),
                "runs_today": r["runs_today"] or 0,
                "total_runs": int(r["total_runs"]),
                "total_tokens": int(r["total_tokens"]),
                "total_cost": round(float(r["total_cost"]), 4),
            }
            for r in rows
        ],
    }


@router.get("/users/{user_id}")
async def get_user_detail(user_id: UUID, request: Request):
    """Detailed user view with recent activity."""
    _require_admin(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM nf_users WHERE id = $1", user_id)
        if not user:
            raise HTTPException(404, "User not found")

        # Recent runs
        runs = await conn.fetch("""
            SELECT id, status, total_tokens, total_cost_usd, created_at
            FROM workflow_runs WHERE user_id = $1::uuid
            ORDER BY created_at DESC LIMIT 20
        """, str(user_id))

        # Org memberships
        orgs = await conn.fetch("""
            SELECT o.id, o.name, o.slug, om.role
            FROM organization_members om
            JOIN organizations o ON o.id = om.org_id
            WHERE om.user_id = $1
        """, user_id)

        # API keys
        keys = await conn.fetch("""
            SELECT id, key_prefix, name, created_at
            FROM api_keys WHERE user_id = $1::uuid
        """, str(user_id))

    return {
        "user": {
            "id": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "plan": user["plan"] or "free",
            "is_active": user["is_active"],
            "email_verified": user["email_verified"],
            "provider": user["provider"],
            "created_at": user["created_at"].isoformat(),
            "stripe_customer_id": user.get("stripe_customer_id"),
        },
        "recent_runs": [
            {
                "id": str(r["id"]),
                "status": r["status"],
                "tokens": int(r["total_tokens"] or 0),
                "cost": round(float(r["total_cost_usd"] or 0), 4),
                "created_at": r["created_at"].isoformat(),
            }
            for r in runs
        ],
        "organizations": [
            {"id": str(o["id"]), "name": o["name"], "slug": o["slug"], "role": o["role"]}
            for o in orgs
        ],
        "api_keys": [
            {"id": str(k["id"]), "prefix": k["key_prefix"], "name": k["name"]}
            for k in keys
        ],
    }


@router.post("/users/{user_id}/suspend")
async def suspend_user(user_id: UUID, request: Request):
    """Suspend a user account."""
    _require_admin(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE nf_users SET is_active = false WHERE id = $1", user_id
        )
        if result == "UPDATE 0":
            raise HTTPException(404, "User not found")

    logger.info("Admin suspended user %s", user_id)
    return {"suspended": True}


@router.post("/users/{user_id}/activate")
async def activate_user(user_id: UUID, request: Request):
    """Reactivate a suspended user."""
    _require_admin(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE nf_users SET is_active = true WHERE id = $1", user_id
        )
        if result == "UPDATE 0":
            raise HTTPException(404, "User not found")

    logger.info("Admin activated user %s", user_id)
    return {"activated": True}


@router.get("/orgs")
async def list_orgs(request: Request, skip: int = 0, limit: int = 50):
    """List all organizations."""
    _require_admin(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT o.*,
                   (SELECT count(*) FROM organization_members WHERE org_id = o.id) AS members,
                   (SELECT COALESCE(SUM(wr.total_tokens), 0) FROM workflow_runs wr WHERE wr.org_id = o.id) AS total_tokens
            FROM organizations o
            ORDER BY o.created_at DESC
            LIMIT $1 OFFSET $2
        """, limit, skip)

    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "slug": r["slug"],
            "plan": r["plan"],
            "is_active": r["is_active"],
            "members": r["members"],
            "total_tokens": int(r["total_tokens"]),
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/usage")
async def global_usage(request: Request, days: int = Query(30, ge=1, le=365)):
    """Global usage analytics."""
    _require_admin(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Daily breakdown
        daily = await conn.fetch("""
            SELECT date_trunc('day', created_at)::date AS day,
                   count(*) AS runs,
                   count(*) FILTER (WHERE status = 'completed') AS completed,
                   COALESCE(SUM(total_tokens), 0) AS tokens,
                   COALESCE(SUM(total_cost_usd), 0) AS cost
            FROM workflow_runs
            WHERE created_at > now() - make_interval(days => $1)
            GROUP BY 1 ORDER BY 1
        """, days)

        # Top users by usage
        top_users = await conn.fetch("""
            SELECT u.email, u.plan, count(wr.id) AS runs,
                   COALESCE(SUM(wr.total_tokens), 0) AS tokens,
                   COALESCE(SUM(wr.total_cost_usd), 0) AS cost
            FROM workflow_runs wr
            JOIN nf_users u ON u.id = wr.user_id::uuid
            WHERE wr.created_at > now() - make_interval(days => $1)
            GROUP BY u.email, u.plan
            ORDER BY tokens DESC LIMIT 10
        """, days)

    return {
        "period_days": days,
        "daily": [
            {
                "date": str(d["day"]),
                "runs": d["runs"],
                "completed": d["completed"],
                "tokens": int(d["tokens"]),
                "cost": round(float(d["cost"]), 4),
            }
            for d in daily
        ],
        "top_users": [
            {
                "email": u["email"],
                "plan": u["plan"],
                "runs": u["runs"],
                "tokens": int(u["tokens"]),
                "cost": round(float(u["cost"]), 4),
            }
            for u in top_users
        ],
    }


@router.get("/audit")
async def global_audit(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Global audit log — all actions across all users."""
    _require_admin(request)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT al.*, u.email
            FROM audit_logs al
            LEFT JOIN nf_users u ON u.id = al.user_id::uuid
            ORDER BY al.created_at DESC
            LIMIT $1 OFFSET $2
        """, limit, skip)

    return [
        {
            "id": str(r["id"]),
            "user_email": r["email"],
            "action": r["action"],
            "entity_type": r["entity_type"],
            "entity_id": r.get("entity_id"),
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


# ── H-2 followup (2026-04-27): admin refresh-token revocation ───────────────
#
# When refresh tokens are enabled (`ENABLE_REFRESH_TOKENS=true`), an
# admin needs a way to forcibly invalidate a user's long-lived refresh
# credential — for account compromise response, plan downgrade, or any
# forced sign-out. Until this commit operators had to drop into a
# Python shell on the running container via `render exec`. Now there
# is a real endpoint.

@router.post("/users/{user_id}/refresh-tokens/revoke-all")
async def admin_revoke_all_refresh_tokens(user_id: UUID, request: Request):
    """Revoke every refresh token for a user. Admin-only.

    Returns the count of tokens that were actually deleted. After
    this call, the user's existing access JWT continues to work
    until its 15-minute (or legacy 8-hour) expiry, but they cannot
    mint a new access token — re-authentication is required.

    For an immediate-cutoff response, pair this call with
    `revoke_jti(...)` on every active access token for the user,
    or rotate `JWT_SIGNING_SECRET` (kills ALL access tokens
    platform-wide).
    """
    _require_admin(request)

    from app.auth.refresh import revoke_all_for_user
    deleted = await revoke_all_for_user(str(user_id))

    logger.info(
        "Admin revoked all refresh tokens for user=%s count=%d",
        str(user_id)[:8], deleted,
    )
    return {"user_id": str(user_id), "revoked_count": deleted}
