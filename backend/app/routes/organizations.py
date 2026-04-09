"""Organization management — multi-tenant CRUD for SaaS.

Endpoints:
  POST   /organizations/         — Create organization
  GET    /organizations/         — List user's organizations
  GET    /organizations/{id}     — Get organization details
  POST   /organizations/{id}/invite  — Invite member
  DELETE /organizations/{id}/members/{user_id} — Remove member
  PUT    /organizations/{id}     — Update organization
"""

import logging
import re
from uuid import UUID
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.db.client import get_db_pool
from app.auth.jwt_handler import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["organizations"])


class CreateOrgRequest(BaseModel):
    name: str
    slug: str = ""


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "member"  # owner, admin, member, viewer


class UpdateOrgRequest(BaseModel):
    name: Optional[str] = None
    settings: Optional[dict] = None


def _get_user_id(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user.get("sub", user.get("user_id", ""))


def _slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug[:50]


@router.post("/", status_code=201)
async def create_organization(body: CreateOrgRequest, request: Request):
    """Create a new organization. Creator becomes owner."""
    user_id = _get_user_id(request)
    slug = body.slug or _slugify(body.name)

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Check slug uniqueness
            existing = await conn.fetchrow("SELECT id FROM organizations WHERE slug = $1", slug)
            if existing:
                raise HTTPException(409, f"Organization slug '{slug}' already exists")

            # Create org
            org = await conn.fetchrow(
                """INSERT INTO organizations (name, slug)
                   VALUES ($1, $2) RETURNING id, name, slug, plan, created_at""",
                body.name, slug,
            )

            # Add creator as owner
            await conn.execute(
                """INSERT INTO organization_members (org_id, user_id, role)
                   VALUES ($1, $2::uuid, 'owner')""",
                org["id"], user_id,
            )

        return {
            "id": str(org["id"]),
            "name": org["name"],
            "slug": org["slug"],
            "plan": org["plan"],
            "role": "owner",
            "created_at": org["created_at"].isoformat(),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create organization")
        raise HTTPException(500, "Internal server error")


@router.get("/")
async def list_organizations(request: Request):
    """List all organizations the user belongs to."""
    user_id = _get_user_id(request)

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT o.id, o.name, o.slug, o.plan, o.is_active, o.created_at,
                          om.role, om.joined_at,
                          (SELECT count(*) FROM organization_members WHERE org_id = o.id) AS member_count
                   FROM organizations o
                   JOIN organization_members om ON om.org_id = o.id
                   WHERE om.user_id = $1::uuid
                   ORDER BY om.joined_at ASC""",
                user_id,
            )
        return [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "slug": r["slug"],
                "plan": r["plan"],
                "is_active": r["is_active"],
                "role": r["role"],
                "member_count": r["member_count"],
                "joined_at": r["joined_at"].isoformat(),
            }
            for r in rows
        ]
    except Exception:
        logger.exception("Failed to list organizations")
        raise HTTPException(500, "Internal server error")


@router.get("/{org_id}")
async def get_organization(org_id: UUID, request: Request):
    """Get organization details with members."""
    user_id = _get_user_id(request)

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify membership
            membership = await conn.fetchrow(
                "SELECT role FROM organization_members WHERE org_id = $1 AND user_id = $2::uuid",
                org_id, user_id,
            )
            if not membership:
                raise HTTPException(404, "Organization not found")

            org = await conn.fetchrow("SELECT * FROM organizations WHERE id = $1", org_id)
            members = await conn.fetch(
                """SELECT om.user_id, om.role, om.joined_at, u.email, u.name
                   FROM organization_members om
                   JOIN nf_users u ON u.id = om.user_id
                   WHERE om.org_id = $1
                   ORDER BY om.joined_at""",
                org_id,
            )

        return {
            "id": str(org["id"]),
            "name": org["name"],
            "slug": org["slug"],
            "plan": org["plan"],
            "is_active": org["is_active"],
            "settings": org["settings"],
            "created_at": org["created_at"].isoformat(),
            "your_role": membership["role"],
            "members": [
                {
                    "user_id": str(m["user_id"]),
                    "email": m["email"],
                    "name": m["name"],
                    "role": m["role"],
                    "joined_at": m["joined_at"].isoformat(),
                }
                for m in members
            ],
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get organization")
        raise HTTPException(500, "Internal server error")


@router.post("/{org_id}/invite")
async def invite_member(org_id: UUID, body: InviteMemberRequest, request: Request):
    """Invite a user to the organization. Requires admin/owner role."""
    user_id = _get_user_id(request)

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify admin/owner
            membership = await conn.fetchrow(
                "SELECT role FROM organization_members WHERE org_id = $1 AND user_id = $2::uuid",
                org_id, user_id,
            )
            if not membership or membership["role"] not in ("owner", "admin"):
                raise HTTPException(403, "Only admins can invite members")

            # Find user by email
            invitee = await conn.fetchrow("SELECT id FROM nf_users WHERE email = $1", body.email)
            if not invitee:
                raise HTTPException(404, f"User {body.email} not found. They must register first.")

            # Check already member
            existing = await conn.fetchrow(
                "SELECT id FROM organization_members WHERE org_id = $1 AND user_id = $2",
                org_id, invitee["id"],
            )
            if existing:
                raise HTTPException(409, "User is already a member")

            # Check seat limit
            org = await conn.fetchrow("SELECT max_seats FROM organizations WHERE id = $1", org_id)
            count = await conn.fetchval("SELECT count(*) FROM organization_members WHERE org_id = $1", org_id)
            if org and count >= org["max_seats"]:
                raise HTTPException(403, f"Seat limit reached ({org['max_seats']}). Upgrade plan.")

            await conn.execute(
                """INSERT INTO organization_members (org_id, user_id, role, invited_by)
                   VALUES ($1, $2, $3, $4::uuid)""",
                org_id, invitee["id"], body.role, user_id,
            )

        return {"invited": True, "email": body.email, "role": body.role}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to invite member")
        raise HTTPException(500, "Internal server error")


@router.delete("/{org_id}/members/{member_id}")
async def remove_member(org_id: UUID, member_id: UUID, request: Request):
    """Remove a member from the organization."""
    user_id = _get_user_id(request)

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            membership = await conn.fetchrow(
                "SELECT role FROM organization_members WHERE org_id = $1 AND user_id = $2::uuid",
                org_id, user_id,
            )
            if not membership or membership["role"] not in ("owner", "admin"):
                raise HTTPException(403, "Only admins can remove members")

            if str(member_id) == user_id:
                raise HTTPException(400, "Cannot remove yourself")

            result = await conn.execute(
                "DELETE FROM organization_members WHERE org_id = $1 AND user_id = $2",
                org_id, member_id,
            )
            if result == "DELETE 0":
                raise HTTPException(404, "Member not found")

        return {"removed": True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "Internal server error")
