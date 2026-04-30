"""Contract tests for the 5 highest-traffic route files.

T1.2 from the 2026-04-30 triangulation. Until this commit only
auth and admin had any TestClient-style contract coverage. The
busy product paths (workflows / executions / automations / results
/ workflow_runs) had ZERO route-level tests. A schema or auth
regression in any of them could ship without a single test
failing in CI.

Strategy: this file pins the AUTH and SCHEMA contract for each
endpoint without touching the database. A handful of endpoints
genuinely need DB to exercise their happy path — those stay as
integration coverage in test_full_system.py. What we get here:

  - 401 when Authorization header is missing or invalid (catches
    the case where someone removes `_get_user_id(request)` calls
    in a future refactor).
  - 422 when the Pydantic body fails validation (catches schema
    drift in WorkflowCreate / ExecutionCreate / etc.).
  - Endpoints that exist still exist (route inventory pinned).

The router is mounted bare on a fresh FastAPI app per route file
— no auth middleware, no lifespan. Each endpoint's own
`_get_user_id` (or equivalent) is what enforces auth, so we test
it directly without needing the global middleware.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from uuid import uuid4

from app.auth.jwt_handler import create_token


# ─── helpers ─────────────────────────────────────────────────────────


def _client_for(router) -> TestClient:
    """Build a TestClient with the given router mounted bare. No auth
    middleware; the route's own _get_user_id is what we're testing."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _auth(role: str = "member") -> dict:
    """Return a Bearer-token Authorization header for a member user."""
    token = create_token("test-user-id", "test@nexusforge.ai", role)
    return {"Authorization": f"Bearer {token}"}


# ─── workflows ───────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def workflows_client():
    from app.routes.workflows import router
    return _client_for(router)


def test_workflows_create_requires_auth(workflows_client):
    """POST / without Authorization should not succeed. FastAPI
    parses the Pydantic body before the handler runs, so an
    invalid body returns 422 before the in-handler auth check
    raises 401. Either response is acceptable — what we're
    guarding against is a refactor that drops the auth check
    entirely (which would produce 201 with a fake/null user)."""
    resp = workflows_client.post("/", json={"name": "x", "dag_definition": {}})
    assert resp.status_code in (401, 422)
    assert resp.status_code not in (200, 201)


def test_workflows_create_rejects_missing_required_fields(workflows_client):
    """With a valid token, POST with empty body → 422 from Pydantic."""
    resp = workflows_client.post("/", json={}, headers=_auth())
    assert resp.status_code == 422


def test_workflows_list_requires_auth(workflows_client):
    resp = workflows_client.get("/")
    assert resp.status_code == 401


def test_workflows_get_requires_auth(workflows_client):
    resp = workflows_client.get(f"/{uuid4()}")
    assert resp.status_code == 401


def test_workflows_update_requires_auth(workflows_client):
    resp = workflows_client.put(f"/{uuid4()}", json={"name": "x"})
    assert resp.status_code == 401


def test_workflows_delete_requires_auth(workflows_client):
    resp = workflows_client.delete(f"/{uuid4()}")
    assert resp.status_code == 401


def test_workflows_get_with_invalid_uuid_returns_422(workflows_client):
    """Non-UUID path param → 422 from FastAPI's UUID converter,
    BEFORE auth check (path validation is FastAPI-built-in)."""
    resp = workflows_client.get("/not-a-uuid", headers=_auth())
    assert resp.status_code == 422


# ─── executions ──────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def executions_client():
    from app.routes.executions import router
    return _client_for(router)


def test_executions_create_requires_auth(executions_client):
    resp = executions_client.post("/", json={"workflow_id": str(uuid4()), "input_data": {}})
    assert resp.status_code == 401


def test_executions_list_requires_auth(executions_client):
    resp = executions_client.get("/")
    assert resp.status_code == 401


def test_executions_get_requires_auth(executions_client):
    resp = executions_client.get(f"/{uuid4()}")
    assert resp.status_code == 401


def test_executions_delete_requires_auth(executions_client):
    resp = executions_client.delete(f"/{uuid4()}")
    assert resp.status_code == 401


# ─── automations ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def automations_client():
    from app.routes.automations import router
    return _client_for(router)


def test_automations_list_gracefully_degrades_for_guests(automations_client):
    """`automations.list_automations` returns an empty list for
    unauthenticated callers instead of 401 (graceful degradation —
    documented inline at routes/automations.py:174). Pin the
    contract: response should be 200 with an empty list, NOT a
    500 (DB error) or 401."""
    resp = automations_client.get("/automations/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_automations_create_blocks_writes_for_guests(automations_client):
    """Mutations are NOT graceful-degrade. Without auth or with a
    bad body, must NOT succeed."""
    resp = automations_client.post("/automations/", json={
        "name": "test",
        "workflow_id": str(uuid4()),
        "trigger_type": "manual",
    })
    assert resp.status_code not in (200, 201)


def test_automations_update_blocks_for_guests(automations_client):
    resp = automations_client.put(f"/automations/{uuid4()}", json={"name": "x"})
    assert resp.status_code not in (200, 201)


def test_automations_delete_blocks_for_guests(automations_client):
    resp = automations_client.delete(f"/automations/{uuid4()}")
    assert resp.status_code not in (200, 201, 204)


def test_automations_run_blocks_for_guests(automations_client):
    resp = automations_client.post(f"/automations/{uuid4()}/run", json={})
    assert resp.status_code not in (200, 201)


def test_automations_dashboard_gracefully_degrades_for_guests(automations_client):
    """`automations.get_automation_dashboard` returns empty dashboard
    structure for guests (routes/automations.py:478)."""
    resp = automations_client.get(f"/automations/{uuid4()}/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert "automation" in body and "stats" in body and "recent_runs" in body


# ─── results ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def results_client():
    from app.routes.results import router
    return _client_for(router)


def test_results_list_for_automation_gracefully_degrades(results_client):
    """`results.list_results` returns empty paginated structure for
    guests (results.py:50). Pin: 200 + items=[], NOT 401 or 500."""
    resp = results_client.get(f"/results/automation/{uuid4()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"items": [], "total": 0}


def test_results_pending_approvals_gracefully_degrades(results_client):
    resp = results_client.get("/results/pending-approvals")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"items": [], "total": 0}


def test_results_get_by_id_blocks_for_guests(results_client):
    """Single-result GET does NOT graceful-degrade — it raises a
    proper error (401, 404, or 500 depending on whether DB is up).
    Just pin "not 200"."""
    resp = results_client.get(f"/results/{uuid4()}")
    assert resp.status_code != 200


def test_results_create_blocks_for_guests(results_client):
    resp = results_client.post("/results/", json={
        "automation_id": str(uuid4()),
        "result_data": {},
    })
    assert resp.status_code not in (200, 201)


def test_results_approval_blocks_for_guests(results_client):
    resp = results_client.post(f"/results/{uuid4()}/approval", json={"approved": True})
    assert resp.status_code not in (200, 201)


def test_results_delete_blocks_for_guests(results_client):
    resp = results_client.delete(f"/results/{uuid4()}")
    assert resp.status_code not in (200, 201, 204)


# ─── workflow_runs ───────────────────────────────────────────────────


@pytest.fixture(scope="module")
def runs_client():
    from app.routes.workflow_runs import router
    return _client_for(router)


def test_runs_list_requires_auth(runs_client):
    resp = runs_client.get("/runs/")
    assert resp.status_code == 401


def test_runs_get_requires_auth(runs_client):
    resp = runs_client.get(f"/runs/{uuid4()}")
    assert resp.status_code == 401


# NOTE: `/runs/{run_id}/steps`, `/events`, `/metrics`, `/timeline`
# are intentionally PUBLIC (no _get_user_id call in workflow_runs.py
# at lines 285, 292, 299, 308 — they read from an in-memory
# collector keyed by run_id). The frontend execution-detail page
# polls them anonymously. Pinning auth here would break that UX.
# We test instead that the routes are mounted (returning the canned
# "empty" body for unknown run_id, NOT 404 for missing route or
# 500 for crashed handler).


def test_runs_steps_returns_empty_for_unknown_id(runs_client):
    resp = runs_client.get(f"/runs/{uuid4()}/steps")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"steps": [], "total": 0}


def test_runs_events_returns_empty_for_unknown_id(runs_client):
    resp = runs_client.get(f"/runs/{uuid4()}/events")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"events": [], "total": 0}


def test_runs_metrics_returns_404_for_unknown_id(runs_client):
    """`get_run_metrics` raises 404 when the in-memory collector has
    no entry for this run_id. Pin that contract — should NOT be 200
    (would mean the public endpoint leaked someone else's data)."""
    resp = runs_client.get(f"/runs/{uuid4()}/metrics")
    assert resp.status_code == 404


def test_runs_timeline_returns_404_for_unknown_id(runs_client):
    resp = runs_client.get(f"/runs/{uuid4()}/timeline")
    assert resp.status_code == 404


# ─── reliability endpoints (workflow_runs subset) ────────────────────


def test_runs_reliability_health_requires_auth(runs_client):
    """Even the reliability/health endpoint requires auth — there is
    a separate top-level /api/health for unauthenticated readiness."""
    resp = runs_client.get("/runs/reliability/health")
    assert resp.status_code == 401


def test_runs_reliability_agents_is_public(runs_client):
    """Agent reliability scores are aggregated, anonymous metrics —
    deliberately public (workflow_runs.py:220 takes no `request`
    argument). Pin 200 so a future refactor adding auth here doesn't
    silently break the public dashboard."""
    resp = runs_client.get("/runs/reliability/agents")
    assert resp.status_code == 200
    body = resp.json()
    assert "agents" in body
    assert isinstance(body["agents"], list)


# ─── happy path: invalid token rejected even when present ────────────


def test_workflows_invalid_bearer_rejected(workflows_client):
    """A garbage Bearer must 401 just like a missing one. Catches
    refactors that only check Authorization presence, not validity."""
    resp = workflows_client.get("/", headers={"Authorization": "Bearer garbage.token.here"})
    assert resp.status_code == 401


def test_executions_invalid_bearer_rejected(executions_client):
    resp = executions_client.get("/", headers={"Authorization": "Bearer garbage.token.here"})
    assert resp.status_code == 401
