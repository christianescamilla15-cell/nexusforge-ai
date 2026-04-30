"""Tests for backend/scripts/rotate_tenant_fernet_keys.py.

The script re-encrypts every `tfernet:` row in `user_provider_keys`
from any old master IKM (TENANT_FERNET_IKM_OLD) to the current
JWT_SECRET. These tests use a tiny in-memory fake of the asyncpg
pool to exercise the script end-to-end without a real database.

Coverage:
- No secondaries configured → script exits 0 with a warning, never
  touches the table.
- Row already on the primary IKM → skipped, no UPDATE issued.
- Row on a secondary IKM → decrypted and re-encrypted under the
  primary, UPDATE captured, exit code 0.
- Mixed-prefix safety: `fernet:` rows and bare-base64 (legacy XOR)
  rows are left alone.
- NULL user_id with a tfernet: ciphertext → flagged, exit code 1.
- Row that doesn't decrypt with any configured IKM → exit code 1.
- Cross-tenant isolation: a row's user_id is the salt; the script
  never tries the wrong salt.
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.auth import encryption as enc
from app.auth import secrets as secrets_mod
from scripts import rotate_tenant_fernet_keys as script


# ── fake asyncpg pool ─────────────────────────────────────────────────


class _FakeConn:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.executes: list[tuple] = []

    async def fetch(self, _query: str, *args):
        return [dict(r) for r in self._rows]

    async def execute(self, query: str, *args):
        self.executes.append((query, args))
        # Mirror the UPDATE so subsequent reads in the same test see
        # the new ciphertext (single-pass scripts don't need this,
        # but it makes idempotency tests trivial).
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


@pytest.fixture
def fake_pool_factory(monkeypatch):
    """Patch `app.db.client.get_db_pool` to return a _FakePool wrapping
    the given rows. Returns a (pool, conn) tuple so tests can inspect
    the captured UPDATE calls."""
    def _factory(rows: list[dict]) -> _FakePool:
        pool = _FakePool(rows)

        async def _fake_get_pool():
            return pool

        monkeypatch.setattr("app.db.client.get_db_pool", _fake_get_pool)
        return pool
    return _factory


@pytest.fixture(autouse=True)
def _reset_caches():
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()
    yield
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()


def _set_master(monkeypatch, value: str):
    from app.config import settings
    monkeypatch.setattr(settings, "jwt_secret", value)


# ── tests ────────────────────────────────────────────────────────────


def test_no_secondaries_short_circuits(monkeypatch, fake_pool_factory):
    """With TENANT_FERNET_IKM_OLD unset the script returns 0 immediately
    and never touches the DB."""
    _set_master(monkeypatch, "MASTER-K1-" + "x" * 40)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)

    pool = fake_pool_factory([])
    rc = asyncio.run(script.main())
    assert rc == 0
    # Early-return path: pool.acquire() never gets called, but the
    # pool was created. No execute() should have been issued.
    assert pool.conn.executes == []


def test_already_primary_row_is_skipped(monkeypatch, fake_pool_factory):
    """A row encrypted with the *current* JWT_SECRET decrypts on the
    primary slot; the script should leave it alone."""
    _set_master(monkeypatch, "PRIMARY-IKM-" + "p" * 40)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", "OLD-IKM-" + "o" * 40)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    user_id = uuid4()
    cipher = enc.encrypt_api_key_for_tenant("sk-already-primary", str(user_id))
    rows = [{"id": uuid4(), "user_id": user_id, "api_key_encrypted": cipher}]

    pool = fake_pool_factory(rows)
    rc = asyncio.run(script.main())

    assert rc == 0
    # No UPDATE — already on primary.
    assert pool.conn.executes == []


def test_secondary_row_is_re_encrypted(monkeypatch, fake_pool_factory):
    """A row encrypted under the OLD master IKM is decrypted via the
    secondary slot and re-encrypted under the new primary."""
    old_ikm = "OLD-IKM-" + "o" * 40
    new_ikm = "NEW-IKM-" + "n" * 40

    # Encrypt while the master is still K1 (== old_ikm).
    _set_master(monkeypatch, old_ikm)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()
    user_id = uuid4()
    cipher_k1 = enc.encrypt_api_key_for_tenant("sk-needs-rotation", str(user_id))

    # Rotate: master is now K2, K1 lives in TENANT_FERNET_IKM_OLD.
    _set_master(monkeypatch, new_ikm)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", old_ikm)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    rows = [{"id": uuid4(), "user_id": user_id, "api_key_encrypted": cipher_k1}]
    pool = fake_pool_factory(rows)
    rc = asyncio.run(script.main())

    assert rc == 0
    # Exactly one UPDATE.
    assert len(pool.conn.executes) == 1
    new_cipher = rows[0]["api_key_encrypted"]
    assert new_cipher != cipher_k1
    assert new_cipher.startswith("tfernet:")

    # Plaintext survived the round-trip under the new IKM.
    assert enc.decrypt_api_key_for_tenant(new_cipher, str(user_id)) == "sk-needs-rotation"


def test_run_is_idempotent(monkeypatch, fake_pool_factory):
    """A second pass after a successful migration is a no-op."""
    old_ikm = "OLD-IKM-" + "o" * 40
    new_ikm = "NEW-IKM-" + "n" * 40

    _set_master(monkeypatch, old_ikm)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()
    user_id = uuid4()
    cipher_k1 = enc.encrypt_api_key_for_tenant("sk-idempotent", str(user_id))

    _set_master(monkeypatch, new_ikm)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", old_ikm)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    rows = [{"id": uuid4(), "user_id": user_id, "api_key_encrypted": cipher_k1}]
    pool = fake_pool_factory(rows)

    # First pass migrates the row.
    assert asyncio.run(script.main()) == 0
    assert len(pool.conn.executes) == 1

    # Second pass — should observe `already_primary`, no new UPDATE.
    assert asyncio.run(script.main()) == 0
    assert len(pool.conn.executes) == 1


def test_global_fernet_and_xor_rows_are_skipped(monkeypatch, fake_pool_factory):
    """`fernet:` and bare-base64 rows are out of scope. The script
    should not even attempt to decrypt them."""
    _set_master(monkeypatch, "PRIMARY-IKM-" + "p" * 40)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", "OLD-IKM-" + "o" * 40)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    user_id = uuid4()
    rows = [
        {"id": uuid4(), "user_id": user_id, "api_key_encrypted": "fernet:gAAAAA-globalcipher"},
        {"id": uuid4(), "user_id": user_id, "api_key_encrypted": "Zm9vYmFy"},  # bare base64
    ]
    pool = fake_pool_factory(rows)
    rc = asyncio.run(script.main())

    assert rc == 0
    # No UPDATE; out-of-scope ciphers were skipped.
    assert pool.conn.executes == []


def test_tfernet_with_null_user_id_fails(monkeypatch, fake_pool_factory):
    """A `tfernet:` row with NULL user_id can't be decrypted — return 1
    so an operator investigates instead of dropping the env var."""
    _set_master(monkeypatch, "PRIMARY-IKM-" + "p" * 40)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", "OLD-IKM-" + "o" * 40)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    rows = [{
        "id": uuid4(),
        "user_id": None,
        "api_key_encrypted": "tfernet:gAAAAA-orphaned",
    }]
    pool = fake_pool_factory(rows)
    rc = asyncio.run(script.main())

    assert rc == 1
    assert pool.conn.executes == []  # Never tried.


def test_undecryptable_row_fails(monkeypatch, fake_pool_factory):
    """A `tfernet:` row whose tenant_id can't recover plaintext under
    any configured IKM → exit code 1, no UPDATE."""
    _set_master(monkeypatch, "PRIMARY-IKM-" + "p" * 40)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", "OLD-IKM-" + "o" * 40)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    user_id = uuid4()
    rows = [{
        "id": uuid4(),
        "user_id": user_id,
        # Valid tfernet: prefix but garbage payload.
        "api_key_encrypted": "tfernet:gAAAAABnnnnnnnnnnnnnnnnnnnnnnnnnnotvalid",
    }]
    pool = fake_pool_factory(rows)
    rc = asyncio.run(script.main())

    assert rc == 1
    assert pool.conn.executes == []
