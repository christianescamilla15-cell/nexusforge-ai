"""Tests for the H-2 Phase 1 secret accessors.

Covers:
- Default (no dedicated env vars set) → all three derive from
  JWT_SECRET (back-compat).
- Each dedicated env var, when set, overrides the JWT_SECRET fallback.
- Fernet primary key shape: 44-char base64 even when input is short.
- Fernet secondary list parses comma-separated values.
- boot_fingerprints() returns sha256[:16] of each derived secret
  and never leaks the secrets themselves.
"""
from __future__ import annotations

import base64
import hashlib

import pytest

from app.auth import secrets as secrets_mod


@pytest.fixture(autouse=True)
def _clear_lru_cache():
    """Each test starts with a fresh accessor cache so monkeypatched
    env vars take effect immediately."""
    secrets_mod.get_jwt_signing_secret.cache_clear()
    secrets_mod.get_mythos_hmac_secret.cache_clear()
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    yield
    secrets_mod.get_jwt_signing_secret.cache_clear()
    secrets_mod.get_mythos_hmac_secret.cache_clear()
    secrets_mod.get_primary_fernet_key.cache_clear()
    secrets_mod.get_fernet_secondary_keys.cache_clear()


# ─── back-compat fallback ─────────────────────────────────────────────

def test_jwt_signing_falls_back_to_master(monkeypatch):
    monkeypatch.delenv("JWT_SIGNING_SECRET", raising=False)
    secrets_mod.get_jwt_signing_secret.cache_clear()
    assert secrets_mod.get_jwt_signing_secret() == secrets_mod._master_secret()


def test_mythos_hmac_falls_back_to_master(monkeypatch):
    monkeypatch.delenv("MYTHOS_HMAC_SECRET", raising=False)
    secrets_mod.get_mythos_hmac_secret.cache_clear()
    assert secrets_mod.get_mythos_hmac_secret() == secrets_mod._master_secret().encode()


def test_fernet_primary_falls_back_to_sha256_of_master(monkeypatch):
    monkeypatch.delenv("FERNET_KEY", raising=False)
    secrets_mod.get_primary_fernet_key.cache_clear()
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(secrets_mod._master_secret().encode()).digest()
    )
    assert secrets_mod.get_primary_fernet_key() == expected


def test_fernet_secondary_empty_when_unset(monkeypatch):
    monkeypatch.delenv("FERNET_KEYS_OLD", raising=False)
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    assert secrets_mod.get_fernet_secondary_keys() == []


# ─── dedicated env vars override ──────────────────────────────────────

def test_jwt_signing_uses_dedicated_var(monkeypatch):
    monkeypatch.setenv("JWT_SIGNING_SECRET", "dedicated-jwt-only-" + "x" * 32)
    secrets_mod.get_jwt_signing_secret.cache_clear()
    assert secrets_mod.get_jwt_signing_secret() == "dedicated-jwt-only-" + "x" * 32


def test_mythos_hmac_uses_dedicated_var(monkeypatch):
    monkeypatch.setenv("MYTHOS_HMAC_SECRET", "mythos-only-secret-" + "y" * 32)
    secrets_mod.get_mythos_hmac_secret.cache_clear()
    assert secrets_mod.get_mythos_hmac_secret() == ("mythos-only-secret-" + "y" * 32).encode()


def test_fernet_primary_uses_dedicated_var_canonical_form(monkeypatch):
    """A 44-char canonical Fernet key should pass through unchanged."""
    canonical = base64.urlsafe_b64encode(b"x" * 32)  # 44 chars
    monkeypatch.setenv("FERNET_KEY", canonical.decode())
    secrets_mod.get_primary_fernet_key.cache_clear()
    assert secrets_mod.get_primary_fernet_key() == canonical


def test_fernet_primary_dedicated_var_short_input_is_hashed(monkeypatch):
    """A non-canonical input is sha256-derived to the right shape."""
    monkeypatch.setenv("FERNET_KEY", "too-short-not-44-chars")
    secrets_mod.get_primary_fernet_key.cache_clear()
    out = secrets_mod.get_primary_fernet_key()
    # Always 44-char urlsafe base64 of 32 bytes.
    assert len(out) == 44
    assert len(base64.urlsafe_b64decode(out)) == 32


def test_fernet_secondary_parses_comma_list(monkeypatch):
    a = base64.urlsafe_b64encode(b"a" * 32).decode()
    b = base64.urlsafe_b64encode(b"b" * 32).decode()
    monkeypatch.setenv("FERNET_KEYS_OLD", f"{a}, {b}")
    secrets_mod.get_fernet_secondary_keys.cache_clear()
    out = secrets_mod.get_fernet_secondary_keys()
    assert len(out) == 2
    # Whitespace stripped, order preserved.
    assert out[0] == a.encode()
    assert out[1] == b.encode()


# ─── independence: rotating one secret doesn't drag others ───────────

def test_rotating_jwt_signing_does_not_change_mythos_or_fernet(monkeypatch):
    """The whole point of Phase 1: rotate one surface in isolation."""
    monkeypatch.setenv("JWT_SIGNING_SECRET", "ROTATED-JWT-" + "z" * 32)
    monkeypatch.delenv("MYTHOS_HMAC_SECRET", raising=False)
    monkeypatch.delenv("FERNET_KEY", raising=False)
    secrets_mod.get_jwt_signing_secret.cache_clear()
    secrets_mod.get_mythos_hmac_secret.cache_clear()
    secrets_mod.get_primary_fernet_key.cache_clear()

    jwt_fp = hashlib.sha256(secrets_mod.get_jwt_signing_secret().encode()).hexdigest()
    mythos_fp = hashlib.sha256(secrets_mod.get_mythos_hmac_secret()).hexdigest()
    fernet_fp = hashlib.sha256(secrets_mod.get_primary_fernet_key()).hexdigest()

    # JWT rotated → its fingerprint differs from the master-derived ones.
    master_fp = hashlib.sha256(secrets_mod._master_secret().encode()).hexdigest()
    assert jwt_fp != master_fp
    # Mythos + Fernet still derived from master → they DO NOT match
    # the rotated JWT fingerprint.
    assert mythos_fp != jwt_fp
    assert fernet_fp != jwt_fp


# ─── boot fingerprints ────────────────────────────────────────────────

def test_boot_fingerprints_no_secret_leakage():
    fps = secrets_mod.boot_fingerprints()
    assert set(fps) == {
        "jwt_signing", "mythos_hmac", "fernet_primary", "fernet_secondary_count",
    }
    # Each digest is 16 hex chars (8 bytes of sha256).
    for name in ("jwt_signing", "mythos_hmac", "fernet_primary"):
        assert len(fps[name]) == 16
        assert all(c in "0123456789abcdef" for c in fps[name])
    # Secondary count is a string-of-int, not a digest.
    assert fps["fernet_secondary_count"].isdigit()


def test_boot_fingerprints_change_when_rotated(monkeypatch):
    fps_before = secrets_mod.boot_fingerprints()
    monkeypatch.setenv("JWT_SIGNING_SECRET", "rotated-" + "q" * 32)
    secrets_mod.get_jwt_signing_secret.cache_clear()
    fps_after = secrets_mod.boot_fingerprints()
    assert fps_before["jwt_signing"] != fps_after["jwt_signing"]
    # Other surfaces unaffected.
    assert fps_before["fernet_primary"] == fps_after["fernet_primary"]
