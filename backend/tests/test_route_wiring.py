"""Wiring smoke tests for the 5 routes registered on 2026-04-30.

Until that commit these route modules existed in
`backend/app/routes/` but were never `include_router`'d in
`app.main`, so every documented endpoint 404'd. These tests are
the regression net: they assert each router's most-stable endpoint
(GET /health or equivalent) is reachable through the real app
object, so a future refactor that drops a router from main.py
will fail CI.

Auth-light: each route hits an unauthenticated endpoint or one
that doesn't require DB to answer. We're testing wiring, not the
business logic of the underlying agents.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ─── portfolio_copilot ───────────────────────────────────────────────


def test_portfolio_copilot_health_route_exists(client):
    """GET /api/portfolio-copilot/health should be reachable. The
    auth middleware may return 401 for unauthenticated callers —
    that's still proof the router is mounted. We only fail on 404
    (which is what we'd see if the route wasn't wired at all, the
    state this commit fixes)."""
    resp = client.get("/api/portfolio-copilot/health")
    assert resp.status_code != 404


# ─── orchestrator ────────────────────────────────────────────────────


def test_orchestrator_snapshot_route_exists(client):
    """GET /api/orchestrator/snapshot should be reachable. We accept
    200 OR 5xx (the underlying memory backend may not be configured
    in the test env), but we DO NOT accept 404 — that would mean the
    router isn't mounted."""
    resp = client.get("/api/orchestrator/snapshot")
    assert resp.status_code != 404


# ─── evaluation ──────────────────────────────────────────────────────


def test_evaluation_scenarios_route_exists(client):
    """GET /api/evaluation/scenarios should be reachable. DB may not
    be available in tests; we only assert the route is mounted (not
    404). Auth might also reject — that's fine for this smoke test."""
    resp = client.get("/api/evaluation/scenarios")
    assert resp.status_code != 404


# ─── executions_db ───────────────────────────────────────────────────


def test_executions_db_root_route_exists(client):
    """GET /api/executions-db/ should be reachable (200 or auth/DB
    error, but not 404)."""
    resp = client.get("/api/executions-db/")
    assert resp.status_code != 404


# ─── meta (already has /api/meta prefix internally) ──────────────────


def test_meta_health_is_reachable(client):
    """GET /api/meta/health should be reachable. Verifies the
    meta_router is mounted WITHOUT an extra /api prefix (otherwise
    the path would be /api/api/meta/health and this would 404)."""
    resp = client.get("/api/meta/health")
    assert resp.status_code != 404


# ─── audit / activity de-shadowing (2026-04-30) ──────────────────────


def test_api_audit_resolves_to_compliance_audit_router(client):
    """Until 2026-04-30, two routers both claimed `prefix="/audit"`:
    `app/auth/audit.py` (per-user activity log + SQL bug) and
    `app/routes/audit.py` (compliance audit log with entity-level
    tracking + CSV export). The activity-log router was registered
    first and silently shadowed the compliance-audit routes — the
    main audit page in production was empty / 500'd. This commit
    moved the activity-log to `/api/activity/*`. We assert here
    that `/api/audit/export` (which only exists in the compliance
    router) is now reachable, proving the de-shadowing worked."""
    resp = client.get("/api/audit/export")
    assert resp.status_code != 404


def test_api_audit_entity_route_exists(client):
    """`/api/audit/entity/{type}/{id}` only exists in the compliance
    router. If the activity-log router were still shadowing
    `/api/audit/`, FastAPI would still resolve the path (the
    compliance router has the unique handler), but adding this
    test guards against future re-shadowing if someone re-uses
    `/audit` as a prefix on a third module."""
    from uuid import uuid4
    resp = client.get(f"/api/audit/entity/automation/{uuid4()}")
    assert resp.status_code != 404


def test_api_activity_summary_route_exists(client):
    """The activity-log router (formerly at `/audit/summary`) now
    lives at `/api/activity/summary`. Smoke test."""
    resp = client.get("/api/activity/summary")
    assert resp.status_code != 404


# ─── Mythos key fingerprint in scan reports (2026-04-30) ─────────────


def test_mythos_report_includes_key_fingerprint():
    """AuditReport.to_dict() must include a `mythos_key_fingerprint`
    field — 16-hex sha256 prefix of the active MYTHOS_HMAC_SECRET.
    Lets operators correlate a scan to the key generation in effect.

    Closes the last cosmetic item from the 2026-04-27 H-2 retro.
    Asserted on a fresh AuditReport with no findings (the simplest
    case) so we don't depend on scanner state."""
    import hashlib
    import re

    from app.auth.secrets import get_mythos_hmac_secret
    from app.security.mythos import AuditReport

    out = AuditReport().to_dict()
    fp = out.get("mythos_key_fingerprint")
    assert isinstance(fp, str)
    assert re.fullmatch(r"[0-9a-f]{16}", fp), f"not a 16-hex digest: {fp!r}"

    # Matches sha256[:16] of the active HMAC secret. No leakage of
    # the secret itself.
    expected = hashlib.sha256(get_mythos_hmac_secret()).hexdigest()[:16]
    assert fp == expected
