"""Idempotent seed: create tenant-alpha organization with a single owner.

Creates (or leaves in place) the `tenant-alpha` organization inside the
NexusForge database and links a specified user as the sole `owner`.
Safe to run repeatedly — every write is guarded by ON CONFLICT.

USAGE:
    DATABASE_URL=postgres://... \\
      python backend/scripts/seed_tenant_alpha.py --email you@example.com

    # See what it would do without writing:
    DATABASE_URL=postgres://... \\
      python backend/scripts/seed_tenant_alpha.py --email you@example.com --dry-run

    # If the user does not exist yet, auto-create them:
    DATABASE_URL=postgres://... \\
      python backend/scripts/seed_tenant_alpha.py --email you@example.com --create-user

EXIT CODES:
    0  Seed completed (or dry-run succeeded)
    1  Runtime error (DB connection, missing user, etc.)
    2  Invalid arguments

This script connects directly via asyncpg using DATABASE_URL from the
environment so it can run independently of the FastAPI app.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass

try:
    import asyncpg
except ImportError:  # pragma: no cover
    print("ERROR: asyncpg not installed. Run: pip install asyncpg", file=sys.stderr)
    sys.exit(2)


TENANT_SLUG = "tenant-alpha"
TENANT_NAME = "Alpha Corp"
TENANT_PLAN = "enterprise"
TENANT_SETTINGS = {
    "showcase": True,
    "description": "Synthetic tenant used for the NexusForge modernization showcase.",
}


@dataclass
class SeedResult:
    org_id: str
    org_created: bool
    user_id: str
    user_created: bool
    membership_created: bool


async def _get_or_create_user(
    conn: asyncpg.Connection,
    email: str,
    create_if_missing: bool,
    dry_run: bool,
) -> tuple[str, bool]:
    row = await conn.fetchrow("SELECT id FROM nf_users WHERE email = $1", email)
    if row:
        return str(row["id"]), False

    if not create_if_missing:
        raise RuntimeError(
            f"User {email!r} not found in nf_users. Re-run with --create-user to "
            "insert a new row, or seed the user via the regular sign-up flow first."
        )

    if dry_run:
        return "(new-user-uuid)", True

    row = await conn.fetchrow(
        """
        INSERT INTO nf_users (email, name, provider, role, plan, is_active)
        VALUES ($1, $2, 'email', 'owner', 'enterprise', true)
        ON CONFLICT (email) DO UPDATE SET updated_at = now()
        RETURNING id
        """,
        email,
        email.split("@")[0].title(),
    )
    return str(row["id"]), True


async def _get_or_create_org(
    conn: asyncpg.Connection, dry_run: bool
) -> tuple[str, bool]:
    row = await conn.fetchrow("SELECT id FROM organizations WHERE slug = $1", TENANT_SLUG)
    if row:
        return str(row["id"]), False

    if dry_run:
        return "(new-org-uuid)", True

    row = await conn.fetchrow(
        """
        INSERT INTO organizations
            (name, slug, plan, max_seats, is_active, settings)
        VALUES ($1, $2, $3, 10, true, $4::jsonb)
        ON CONFLICT (slug) DO UPDATE SET updated_at = now()
        RETURNING id
        """,
        TENANT_NAME,
        TENANT_SLUG,
        TENANT_PLAN,
        '{"showcase": true, "description": "Synthetic tenant used for the NexusForge modernization showcase."}',
    )
    return str(row["id"]), True


async def _ensure_owner_membership(
    conn: asyncpg.Connection, org_id: str, user_id: str, dry_run: bool
) -> bool:
    """Link the user to the org as owner. Returns True if row was inserted."""
    if dry_run:
        existing = await conn.fetchrow(
            "SELECT 1 FROM organization_members WHERE org_id = $1::uuid AND user_id = $2::uuid",
            org_id if org_id != "(new-org-uuid)" else None,
            user_id if user_id != "(new-user-uuid)" else None,
        ) if not org_id.startswith("(") else None
        return existing is None

    result = await conn.execute(
        """
        INSERT INTO organization_members (org_id, user_id, role, joined_at)
        VALUES ($1::uuid, $2::uuid, 'owner', now())
        ON CONFLICT (org_id, user_id) DO UPDATE SET role = 'owner'
        """,
        org_id,
        user_id,
    )
    return result.endswith("1")  # "INSERT 0 1" on new insert


async def seed(email: str, create_user: bool, dry_run: bool) -> SeedResult:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    conn = await asyncpg.connect(database_url)
    try:
        if dry_run:
            # Run everything inside a transaction that we roll back at the end.
            async with conn.transaction():
                user_id, user_created = await _get_or_create_user(
                    conn, email, create_user, dry_run=True
                )
                org_id, org_created = await _get_or_create_org(conn, dry_run=True)
                membership_created = await _ensure_owner_membership(
                    conn, org_id, user_id, dry_run=True
                )
                raise _DryRunRollback(
                    SeedResult(
                        org_id=org_id,
                        org_created=org_created,
                        user_id=user_id,
                        user_created=user_created,
                        membership_created=membership_created,
                    )
                )
        else:
            async with conn.transaction():
                user_id, user_created = await _get_or_create_user(
                    conn, email, create_user, dry_run=False
                )
                org_id, org_created = await _get_or_create_org(conn, dry_run=False)
                membership_created = await _ensure_owner_membership(
                    conn, org_id, user_id, dry_run=False
                )
                return SeedResult(
                    org_id=org_id,
                    org_created=org_created,
                    user_id=user_id,
                    user_created=user_created,
                    membership_created=membership_created,
                )
    except _DryRunRollback as rollback:
        return rollback.result
    finally:
        await conn.close()


class _DryRunRollback(Exception):
    """Sentinel that carries the dry-run result out of the transaction block."""

    def __init__(self, result: SeedResult) -> None:
        self.result = result
        super().__init__("dry-run rollback")


def _print_result(result: SeedResult, dry_run: bool) -> None:
    print()
    print("=" * 60)
    print(f"Tenant seed report{' (DRY-RUN)' if dry_run else ''}")
    print("=" * 60)
    print(f"Organization slug:   {TENANT_SLUG}")
    print(f"Organization name:   {TENANT_NAME}")
    print(f"Organization id:     {result.org_id}")
    print(f"  {'created' if result.org_created else 'already existed'}")
    print(f"Owner user id:       {result.user_id}")
    print(f"  {'created' if result.user_created else 'already existed'}")
    print(
        f"Ownership link:      "
        f"{'created' if result.membership_created else 'already in place'}"
    )
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--email",
        required=True,
        help="Email of the user who should be the sole owner of tenant-alpha",
    )
    parser.add_argument(
        "--create-user",
        action="store_true",
        help="Create the user if they do not already exist in nf_users",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing to the database",
    )
    args = parser.parse_args()

    try:
        result = asyncio.run(
            seed(
                email=args.email,
                create_user=args.create_user,
                dry_run=args.dry_run,
            )
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except asyncpg.PostgresError as exc:
        print(f"DATABASE ERROR: {exc}", file=sys.stderr)
        return 1

    _print_result(result, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
