"""Tests for the H-2 Phase 2 MultiFernet rotation overlap.

The scenario being verified:
  1. Encrypt some API keys with the old `FERNET_KEY` (call it K1).
  2. Operator generates K2, sets `FERNET_KEY=K2` and
     `FERNET_KEYS_OLD=K1`. The deploy now runs MultiFernet([K2, K1]).
  3. New encrypts use K2 (the primary); decrypts of K1-ciphertext
     still succeed via the secondary slot.
  4. Migration script (Phase 4, separate commit) re-encrypts every
     row from K1 to K2.
  5. Operator drops `FERNET_KEYS_OLD`; the deploy now runs
     single-Fernet on K2 and old K1 ciphertexts would no longer
     decrypt — but they have all been migrated by step 4.

These tests cover steps 1-3 (the in-process overlap behavior).
Steps 4-5 are operational and live in the migration script + runbook.
"""
from __future__ import annotations

import base64

import pytest

from app.auth import encryption as enc
from app.auth import secrets as secrets_mod


def _fresh_canonical_key() -> str:
    import secrets as _py_secrets
    return base64.urlsafe_b64encode(_py_secrets.token_bytes(32)).decode()


@pytest.fixture(autouse=True)
def _reset_caches():
    """Each test starts with a clean accessor + Fernet cache."""
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()
    yield
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()


def test_single_fernet_when_no_secondaries(monkeypatch):
    """Default deploy (no FERNET_KEYS_OLD) → plain Fernet, not MultiFernet."""
    monkeypatch.setenv("FERNET_KEY", _fresh_canonical_key())
    monkeypatch.delenv("FERNET_KEYS_OLD", raising=False)

    f = enc._get_fernet()
    assert f is not None and f is not False
    # plain Fernet has no `_fernets` attribute (MultiFernet does).
    assert not hasattr(f, "_fernets") or len(getattr(f, "_fernets", [])) == 1 or not hasattr(f, "_fernets")


def test_multifernet_when_secondaries_present(monkeypatch):
    """With FERNET_KEYS_OLD set, the handler is a MultiFernet."""
    primary = _fresh_canonical_key()
    secondary = _fresh_canonical_key()
    monkeypatch.setenv("FERNET_KEY", primary)
    monkeypatch.setenv("FERNET_KEYS_OLD", secondary)

    f = enc._get_fernet()
    # MultiFernet exposes its inner list as `_fernets`.
    assert hasattr(f, "_fernets")
    assert len(f._fernets) == 2  # primary + 1 secondary


def test_rotation_overlap_decrypts_old_ciphertext(monkeypatch):
    """The whole point: encrypt with K1, rotate to K2 with K1 in
    FERNET_KEYS_OLD, then verify the old ciphertext still decrypts."""
    k1 = _fresh_canonical_key()
    k2 = _fresh_canonical_key()

    # Phase A — only K1 is in play; encrypt a value.
    monkeypatch.setenv("FERNET_KEY", k1)
    monkeypatch.delenv("FERNET_KEYS_OLD", raising=False)
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()
    cipher = enc.encrypt_api_key("sk-very-secret-original")
    assert cipher.startswith("fernet:")

    # Phase B — rotate to K2 with K1 as secondary.
    monkeypatch.setenv("FERNET_KEY", k2)
    monkeypatch.setenv("FERNET_KEYS_OLD", k1)
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()

    # Old ciphertext still decrypts.
    assert enc.decrypt_api_key(cipher) == "sk-very-secret-original"

    # New encrypt now uses K2 (it's the primary).
    new_cipher = enc.encrypt_api_key("sk-fresh-after-rotation")
    assert new_cipher != cipher  # different IV at least; different key too
    assert enc.decrypt_api_key(new_cipher) == "sk-fresh-after-rotation"


def test_rotation_dropping_old_key_breaks_only_unmigrated(monkeypatch):
    """After dropping FERNET_KEYS_OLD, only ciphertexts that were
    re-encrypted with K2 still decrypt; K1 ciphertexts are now opaque.
    This is the expected behavior — the migration script must run
    BEFORE the secondary key is dropped."""
    k1 = _fresh_canonical_key()
    k2 = _fresh_canonical_key()

    # Encrypt with K1.
    monkeypatch.setenv("FERNET_KEY", k1)
    monkeypatch.delenv("FERNET_KEYS_OLD", raising=False)
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()
    cipher_k1 = enc.encrypt_api_key("encrypted-with-k1")

    # Rotate to K2, no overlap.
    monkeypatch.setenv("FERNET_KEY", k2)
    monkeypatch.delenv("FERNET_KEYS_OLD", raising=False)
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()

    # K1 ciphertext is now undecryptable (returns "" per
    # `decrypt_api_key`'s exception handler).
    assert enc.decrypt_api_key(cipher_k1) == ""

    # New encrypts with K2 work.
    new_cipher = enc.encrypt_api_key("encrypted-with-k2")
    assert enc.decrypt_api_key(new_cipher) == "encrypted-with-k2"


def test_multiple_secondaries_all_tried(monkeypatch):
    """FERNET_KEYS_OLD can list multiple historical keys."""
    k1 = _fresh_canonical_key()
    k2 = _fresh_canonical_key()
    k3 = _fresh_canonical_key()

    # Encrypt with k1.
    monkeypatch.setenv("FERNET_KEY", k1)
    monkeypatch.delenv("FERNET_KEYS_OLD", raising=False)
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()
    c1 = enc.encrypt_api_key("from-k1")

    # Encrypt with k2.
    monkeypatch.setenv("FERNET_KEY", k2)
    monkeypatch.delenv("FERNET_KEYS_OLD", raising=False)
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()
    c2 = enc.encrypt_api_key("from-k2")

    # Now move to k3 with k1+k2 in the secondary list.
    monkeypatch.setenv("FERNET_KEY", k3)
    monkeypatch.setenv("FERNET_KEYS_OLD", f"{k1},{k2}")
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    enc.reset_fernet_cache()

    # Both old ciphertexts decrypt.
    assert enc.decrypt_api_key(c1) == "from-k1"
    assert enc.decrypt_api_key(c2) == "from-k2"

    # Fresh writes use k3.
    c3 = enc.encrypt_api_key("from-k3")
    assert enc.decrypt_api_key(c3) == "from-k3"
