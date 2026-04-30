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
