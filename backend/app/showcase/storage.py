"""Async storage for persisted showcase runs (Batch 3 deliverable F5).

Thin asyncpg wrapper around the ``showcase_runs`` table. Offers:

- ``save_run``  — insert a new row and return its id
- ``latest_run``  — fetch the most recent row for a tenant_slug
- ``list_tenants``  — enumerate tenants that have at least one row

All JSONB columns are stored with ``json.dumps`` and read back with
``json.loads`` so callers see plain Python dicts either way. Errors
surface as ``StorageError`` so route handlers can cleanly differentiate
between DB failures and missing rows.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.db.client import get_db_pool

logger = logging.getLogger(__name__)


class StorageError(RuntimeError):
    """Raised when the showcase storage layer fails."""


async def save_run(
    tenant_slug: str,
    report: dict[str, Any],
    compliance: dict[str, Any] | None = None,
    strangler_plans: dict[str, Any] | None = None,
    duration_ms: int = 0,
    source: str = "pipeline",
    created_by: str | None = None,
) -> str:
    """Insert a new showcase_runs row and return its UUID as a string.

    Args:
        tenant_slug: Plain slug matching the tenant. No foreign key is
            enforced here — the tenant may or may not have a row in
            ``organizations``.
        report: The full showcase report dict (same shape the /showcase
            endpoint serves today).
        compliance: Optional compliance profile dict. Pass ``None`` if
            the tenant has no compliance block.
        strangler_plans: Mapping from app codename to strangler plan
            dict. Stored as a single JSONB blob for fast retrieval.
        duration_ms: Pipeline wall time in milliseconds.
        source: "pipeline" (default), "seed" (from static fixtures) or
            "import" (external backfill).
        created_by: Optional UUID of the user who triggered the run.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO showcase_runs
                    (tenant_slug, report, compliance, strangler_plans,
                     duration_ms, source, created_by)
                VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5, $6, $7)
                RETURNING id
                """,
                tenant_slug,
                json.dumps(report),
                json.dumps(compliance) if compliance is not None else None,
                json.dumps(strangler_plans or {}),
                duration_ms,
                source,
                created_by,
            )
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("Failed to persist showcase run for %s", tenant_slug)
        raise StorageError(f"save_run failed: {exc}") from exc
    return str(row["id"])


async def latest_run(tenant_slug: str) -> dict[str, Any] | None:
    """Return the most recent row for a tenant, or None if none exist.

    The returned dict has keys: ``id``, ``tenant_slug``, ``generated_at``
    (ISO string), ``report``, ``compliance`` (may be None),
    ``strangler_plans`` (dict), ``duration_ms``, ``source``.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, tenant_slug, generated_at, report, compliance,
                       strangler_plans, duration_ms, source
                FROM showcase_runs
                WHERE tenant_slug = $1
                ORDER BY generated_at DESC
                LIMIT 1
                """,
                tenant_slug,
            )
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("Failed to read latest showcase run for %s", tenant_slug)
        raise StorageError(f"latest_run failed: {exc}") from exc

    if row is None:
        return None

    return {
        "id": str(row["id"]),
        "tenant_slug": row["tenant_slug"],
        "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None,
        "report": _maybe_json(row["report"]),
        "compliance": _maybe_json(row["compliance"]),
        "strangler_plans": _maybe_json(row["strangler_plans"]) or {},
        "duration_ms": row["duration_ms"],
        "source": row["source"],
    }


async def list_tenants() -> list[dict[str, Any]]:
    """Return one summary row per tenant that has at least one run.

    Each entry has ``tenant_slug``, ``latest_generated_at`` and
    ``run_count``. Useful for /api/refactor/showcase to surface both
    persisted and static tenants.
    """
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tenant_slug,
                       MAX(generated_at) AS latest_generated_at,
                       COUNT(*)          AS run_count
                FROM showcase_runs
                GROUP BY tenant_slug
                ORDER BY tenant_slug
                """
            )
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("Failed to list showcase tenants")
        raise StorageError(f"list_tenants failed: {exc}") from exc

    return [
        {
            "tenant_slug": r["tenant_slug"],
            "latest_generated_at": (
                r["latest_generated_at"].isoformat()
                if r["latest_generated_at"]
                else None
            ),
            "run_count": r["run_count"],
        }
        for r in rows
    ]


def _maybe_json(value: Any) -> Any:
    """Decode a JSONB field regardless of asyncpg's return type.

    asyncpg returns JSONB as already-decoded Python objects if a codec
    is registered, or as strings otherwise. We handle both paths so
    callers never see a raw JSON string.
    """
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value
