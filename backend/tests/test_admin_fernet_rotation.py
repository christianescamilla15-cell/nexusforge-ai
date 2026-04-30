"""Tests for the admin Fernet rotation endpoints (2026-04-30).

Covers:
- POST /admin/security/fernet-rotation/global
- POST /admin/security/fernet-rotation/tenant

Both wrap the CLI scripts in `backend/scripts/rotate_*_fernet_keys.py`.
The endpoints are admin-only; non-admin callers should see 404 (not
403, per the existing _require_admin convention that hides admin
endpoints from regular users).

Coverage:
- Non-admin → 404 (info-leak guard).
- Admin + no overlap env var → status="no_op" with reason.
- Admin + overlap configured + rows present → status="complete",
  migrated count > 0, ciphertexts actually rewritten in the fake DB.
- Admin + tenant endpoint with NULL user_id row → status="partial",
  no_user_id_skipped counted.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import encryption as enc
from app.auth import secrets as secrets_mod
from app.routes.admin import router as admin_router


# ── fake asyncpg pool (re-used pattern from test_rotate_tenant_fernet_keys) ──


class _FakeConn:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.executes: list[tuple] = []

    async def fetch(self, _query: str, *args):
        return [dict(r) for r in self._rows]

    async def execute(self, query: str, *args):
        self.executes.append((query, args))
        if query.startswith("UPDATE user_provider_keys"):
            new_cipher, row_id = args
            for r in self._rows:
                if r["id"] == row_id:
                    r["api_key_encrypted"] = new_cipher


class _FakeAcquireCtx:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *_):
        return False


class _FakePool:
    def __init__(self, rows: list[dict]):
        self.conn = _FakeConn(rows)

    def acquire(self):
        return _FakeAcquireCtx(self.conn)


# ── client fixtures with injected auth state ────────────────────────────


def _make_client(role: str | None) -> TestClient:
    """Build a TestClient whose middleware seeds request.state.user
    with the given role. role=None simulates an unauthenticated caller."""
    test_app = FastAPI()

    @test_app.middleware("http")
    async def _inject_user(request, call_next):
        if role is None:
            request.state.user = None
        else:
            request.state.user = {
                "sub": "test-admin-id" if role == "admin" else "test-user-id",
                "email": f"{role}@test.com",
                "role": role,
            }
        return await call_next(request)

    test_app.include_router(admin_router)
    return TestClient(test_app)


@pytest.fixture
def admin_client():
    return _make_client("admin")


@pytest.fixture
def member_client():
    return _make_client("member")


@pytest.fixture
def fake_pool_factory(monkeypatch):
    def _factory(rows: list[dict]) -> _FakePool:
        pool = _FakePool(rows)

        async def _fake_get_pool():
            return pool

        monkeypatch.setattr("app.routes.admin.get_db_pool", _fake_get_pool)
        return pool
    return _factory


@pytest.fixture(autouse=True)
def _reset_caches():
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()
    secrets_mod.get_primary_fernet_key.cache_clear()
    enc.reset_fernet_cache()
    yield
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()
    secrets_mod.get_primary_fernet_key.cache_clear()
    enc.reset_fernet_cache()


def _set_master(monkeypatch, value: str):
    from app.config import settings
    monkeypatch.setattr(settings, "jwt_secret", value)


# ── /admin/security/fernet-rotation/global ─────────────────────────────


def test_global_endpoint_rejects_non_admin(member_client, fake_pool_factory):
    """Non-admin role → 404 (info-leak guard, same as other admin routes)."""
    fake_pool_factory([])
    resp = member_client.post("/admin/security/fernet-rotation/global")
    assert resp.status_code == 404


def test_global_endpoint_no_secondary_returns_no_op(monkeypatch, admin_client, fake_pool_factory):
    """With FERNET_KEYS_OLD unset the endpoint returns 200 with
    status='no_op' and a reason — the operator hasn't set the env var
    yet, this is a configuration state, not a runtime error."""
    monkeypatch.delenv("FERNET_KEYS_OLD", raising=False)
    secrets_mod.get_fernet_secondary_keys.cache_clear()

    fake_pool_factory([])
    resp = admin_client.post("/admin/security/fernet-rotation/global")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_op"
    assert "FERNET_KEYS_OLD" in body["reason"]
    assert body["secondary_count"] == 0
    assert body["migrated"] == 0


def test_global_endpoint_runs_when_secondary_set(monkeypatch, admin_client, fake_pool_factory):
    """With FERNET_KEYS_OLD set + a row encrypted under the OLD key,
    the endpoint runs the migration: status='complete', migrated=1."""
    import base64

    # Build a clean K1 → K2 setup so the row is encrypted under K1
    # while K2 is the current primary.
    k1 = base64.urlsafe_b64encode(b"k1" + b"x" * 30).decode()
    k2 = base64.urlsafe_b64encode(b"k2" + b"y" * 30).decode()

    # Encrypt under K1 first.
    monkeypatch.setenv("FERNET_KEY", k1)
    monkeypatch.delenv("FERNET_KEYS_OLD", raising=False)
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()
    cipher_k1 = enc.encrypt_api_key("sk-needs-rotation")
    assert cipher_k1.startswith("fernet:")

    # Now rotate: K2 is primary, K1 lives in FERNET_KEYS_OLD.
    monkeypatch.setenv("FERNET_KEY", k2)
    monkeypatch.setenv("FERNET_KEYS_OLD", k1)
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()

    rows = [{"id": uuid4(), "api_key_encrypted": cipher_k1}]
    pool = fake_pool_factory(rows)

    resp = admin_client.post("/admin/security/fernet-rotation/global")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert body["migrated"] == 1
    assert body["failed"] == 0
    assert body["already_primary"] == 0
    assert body["secondary_count"] == 1
    # 16-hex fingerprint of the primary key.
    assert len(body["primary_fingerprint"]) == 16

    # The fake pool actually saw the UPDATE.
    assert len(pool.conn.executes) == 1
    new_cipher = rows[0]["api_key_encrypted"]
    assert new_cipher != cipher_k1
    assert new_cipher.startswith("fernet:")


# ── /admin/security/fernet-rotation/tenant ─────────────────────────────


def test_tenant_endpoint_rejects_non_admin(member_client, fake_pool_factory):
    fake_pool_factory([])
    resp = member_client.post("/admin/security/fernet-rotation/tenant")
    assert resp.status_code == 404


def test_tenant_endpoint_no_secondary_returns_no_op(monkeypatch, admin_client, fake_pool_factory):
    _set_master(monkeypatch, "MASTER-K1-" + "x" * 40)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    fake_pool_factory([])
    resp = admin_client.post("/admin/security/fernet-rotation/tenant")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_op"
    assert "TENANT_FERNET_IKM_OLD" in body["reason"]
    assert body["secondary_ikm_count"] == 0


def test_tenant_endpoint_runs_when_secondary_set(monkeypatch, admin_client, fake_pool_factory):
    """K1 → K2 rotation, one row encrypted under K1, endpoint
    re-encrypts under K2."""
    old_ikm = "OLD-IKM-" + "o" * 40
    new_ikm = "NEW-IKM-" + "n" * 40

    _set_master(monkeypatch, old_ikm)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()
    user_id = uuid4()
    cipher_k1 = enc.encrypt_api_key_for_tenant("sk-needs-rotation", str(user_id))

    _set_master(monkeypatch, new_ikm)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", old_ikm)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    rows = [{"id": uuid4(), "user_id": user_id, "api_key_encrypted": cipher_k1}]
    pool = fake_pool_factory(rows)

    resp = admin_client.post("/admin/security/fernet-rotation/tenant")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert body["migrated"] == 1
    assert body["failed"] == 0
    assert body["no_user_id_skipped"] == 0
    assert body["secondary_ikm_count"] == 1

    assert len(pool.conn.executes) == 1
    new_cipher = rows[0]["api_key_encrypted"]
    assert new_cipher.startswith("tfernet:")
    # Round-trip: still decrypts under the same tenant_id with the
    # rotated master in place.
    assert enc.decrypt_api_key_for_tenant(new_cipher, str(user_id)) == "sk-needs-rotation"


def test_tenant_endpoint_partial_when_null_user_id(monkeypatch, admin_client, fake_pool_factory):
    """A `tfernet:` row with NULL user_id can't be migrated — endpoint
    surfaces this as `status='partial'` with `no_user_id_skipped=1`,
    not as a 500 error."""
    _set_master(monkeypatch, "PRIMARY-IKM-" + "p" * 40)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", "OLD-IKM-" + "o" * 40)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    rows = [{
        "id": uuid4(),
        "user_id": None,
        "api_key_encrypted": "tfernet:gAAAAA-orphaned",
    }]
    pool = fake_pool_factory(rows)

    resp = admin_client.post("/admin/security/fernet-rotation/tenant")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "partial"
    assert body["no_user_id_skipped"] == 1
    assert pool.conn.executes == []
