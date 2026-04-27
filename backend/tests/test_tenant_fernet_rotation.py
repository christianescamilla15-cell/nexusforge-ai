"""Tests for the M-10 followup per-tenant Fernet rotation overlap.

Per-tenant Fernet is derived via HKDF from the master keying
material (currently `JWT_SECRET`). Rotating the master used to
brick every `tfernet:` row at once; now `TENANT_FERNET_IKM_OLD`
declares secondary IKMs that participate in decrypt-only via a
MultiFernet wrapper.

Scenarios covered:
- Default (no `TENANT_FERNET_IKM_OLD`) → single Fernet, no
  MultiFernet wrapper (back-compat with M-10 single-IKM behavior).
- One secondary IKM present → encrypt with the previous master,
  rotate, decrypt continues to work.
- Cross-tenant decrypts still fail (different salt → different key
  even with the same IKMs) — the rotation overlap doesn't break
  per-tenant isolation.
- Multiple secondaries are tried in order.
"""
from __future__ import annotations

import os

import pytest

from app.auth import encryption as enc
from app.auth import secrets as secrets_mod


@pytest.fixture(autouse=True)
def _reset_caches():
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()
    yield
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()


def _set_master(monkeypatch, value: str):
    """Rotate the master IKM. The encryption module reads it from
    settings.jwt_secret directly, so we monkeypatch that attribute."""
    from app.config import settings
    monkeypatch.setattr(settings, "jwt_secret", value)


# ─── default behavior (no overlap configured) ────────────────────────

def test_no_secondary_returns_single_fernet():
    """Sanity check: with TENANT_FERNET_IKM_OLD unset, _derive_tenant_fernet
    returns a plain Fernet (the M-10 base case, unchanged)."""
    f = enc._derive_tenant_fernet("user-1")
    # plain Fernet doesn't expose `_fernets` (MultiFernet does).
    assert not hasattr(f, "_fernets")


# ─── overlap roundtrip ───────────────────────────────────────────────

def test_rotation_overlap_decrypts_old_tenant_ciphertext(monkeypatch):
    """Encrypt with K1 (master), then rotate to K2 with K1 as the
    tenant-IKM secondary, verify the K1-era ciphertext still decrypts
    AND new writes use K2."""
    _set_master(monkeypatch, "MASTER-K1-" + "x" * 40)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    cipher_k1 = enc.encrypt_api_key_for_tenant("sk-tenant-secret", "user-1")
    assert cipher_k1.startswith("tfernet:")

    # Rotate: master is now K2, with K1 as secondary IKM.
    _set_master(monkeypatch, "MASTER-K2-" + "y" * 40)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", "MASTER-K1-" + "x" * 40)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    # Old ciphertext still decrypts via the secondary slot.
    assert enc.decrypt_api_key_for_tenant(cipher_k1, "user-1") == "sk-tenant-secret"

    # New encrypt produces a different ciphertext (signed by K2).
    cipher_k2 = enc.encrypt_api_key_for_tenant("fresh-after-rotation", "user-1")
    assert cipher_k2 != cipher_k1
    assert enc.decrypt_api_key_for_tenant(cipher_k2, "user-1") == "fresh-after-rotation"


def test_rotation_overlap_preserves_cross_tenant_isolation(monkeypatch):
    """Even with a MultiFernet stack, user A's ciphertext must NOT
    decrypt under user B's tenant_id — the salt is per-tenant and
    independent of the IKM rotation."""
    _set_master(monkeypatch, "MASTER-K1-" + "z" * 40)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    cipher_a = enc.encrypt_api_key_for_tenant("tenant-A-secret", "user-A")

    # Rotate so a MultiFernet handler is in play.
    _set_master(monkeypatch, "MASTER-K2-" + "w" * 40)
    monkeypatch.setenv("TENANT_FERNET_IKM_OLD", "MASTER-K1-" + "z" * 40)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    # User-A still decrypts.
    assert enc.decrypt_api_key_for_tenant(cipher_a, "user-A") == "tenant-A-secret"

    # User-B does NOT decrypt user-A's ciphertext (returns "" on failure).
    assert enc.decrypt_api_key_for_tenant(cipher_a, "user-B") == ""


def test_dropping_old_ikm_breaks_only_unmigrated(monkeypatch):
    """After dropping TENANT_FERNET_IKM_OLD, K1-era ciphertexts are
    no longer decryptable. This is the expected behavior — the
    migration script must run BEFORE the secondary is dropped."""
    _set_master(monkeypatch, "MASTER-K1-" + "x" * 40)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    cipher_k1 = enc.encrypt_api_key_for_tenant("encrypted-with-k1", "user-1")

    # Hard rotate without overlap.
    _set_master(monkeypatch, "MASTER-K2-" + "y" * 40)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    # Old ciphertext is now opaque.
    assert enc.decrypt_api_key_for_tenant(cipher_k1, "user-1") == ""

    # New writes work under K2.
    new_cipher = enc.encrypt_api_key_for_tenant("encrypted-with-k2", "user-1")
    assert enc.decrypt_api_key_for_tenant(new_cipher, "user-1") == "encrypted-with-k2"


def test_multiple_ikm_secondaries_all_tried(monkeypatch):
    """TENANT_FERNET_IKM_OLD can list multiple historical IKMs."""
    _set_master(monkeypatch, "MASTER-K1-" + "a" * 40)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()
    c1 = enc.encrypt_api_key_for_tenant("from-k1", "user-1")

    _set_master(monkeypatch, "MASTER-K2-" + "b" * 40)
    monkeypatch.delenv("TENANT_FERNET_IKM_OLD", raising=False)
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()
    c2 = enc.encrypt_api_key_for_tenant("from-k2", "user-1")

    # Now move to k3 with both old IKMs in the secondary list.
    _set_master(monkeypatch, "MASTER-K3-" + "c" * 40)
    monkeypatch.setenv(
        "TENANT_FERNET_IKM_OLD",
        "MASTER-K1-" + "a" * 40 + "," + "MASTER-K2-" + "b" * 40,
    )
    secrets_mod.get_tenant_ikm_secondaries.cache_clear()

    assert enc.decrypt_api_key_for_tenant(c1, "user-1") == "from-k1"
    assert enc.decrypt_api_key_for_tenant(c2, "user-1") == "from-k2"

    c3 = enc.encrypt_api_key_for_tenant("from-k3", "user-1")
    assert enc.decrypt_api_key_for_tenant(c3, "user-1") == "from-k3"
