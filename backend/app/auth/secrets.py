"""Centralized secret accessors — H-2 (2026-04-27).

Until this module landed, `JWT_SECRET` was the master key for every
cryptographic surface in NexusForge: JWT signing, Mythos owner-key
HMAC, Fernet API-key encryption. Rotating it bricked all stored API
keys; a leak in one surface compromised all of them.

This module decouples those surfaces. Each accessor reads its own
dedicated env var first; if the dedicated var is unset, falls back to
deriving from `JWT_SECRET` so existing deploys keep working unchanged.

Env vars (all optional today; recommended next deploy):

    JWT_SIGNING_SECRET   — sign / verify JWTs (HS256). Falls back
                           to JWT_SECRET. Rotating this invalidates
                           sessions but does NOT brick stored keys.

    MYTHOS_HMAC_SECRET   — input keying material for the
                           `_derive_mythos_key()` HMAC. Falls back
                           to JWT_SECRET. Rotating only invalidates
                           the X-Mythos-Key value used to call
                           /api/mythos/*.

    FERNET_KEY           — full 32-byte Fernet key (urlsafe-base64,
                           44 chars). Falls back to a SHA-256 of
                           JWT_SECRET. Rotating requires a
                           MultiFernet overlap window (Phase 2).

When all three dedicated vars are set, JWT_SECRET stops being a
master key and becomes a back-compat fallback only. Operators who
want full isolation set the three dedicated vars and clear
JWT_SECRET (it remains required by config validation today; that
will be relaxed in a separate commit once the migration is verified).

Boot-time observability: each accessor logs `dedicated` vs `derived`
so an operator can see at a glance which mode each surface is in.
The hashed fingerprint already emitted by main.py is preserved.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from functools import lru_cache

from app.config import settings

logger = logging.getLogger(__name__)


# ── canonical fallback ──────────────────────────────────────────────────────

def _master_secret() -> str:
    """Back-compat master used when a dedicated env var is unset."""
    return settings.jwt_secret


# ── JWT signing ────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_jwt_signing_secret() -> str:
    """Return the JWT HS256 signing secret.

    Reads `JWT_SIGNING_SECRET`; falls back to `JWT_SECRET`.
    Logged once at first access so the boot log shows the mode.
    """
    dedicated = os.environ.get("JWT_SIGNING_SECRET", "").strip()
    if dedicated:
        logger.info("JWT signing secret: dedicated (JWT_SIGNING_SECRET)")
        return dedicated
    logger.info("JWT signing secret: derived from JWT_SECRET (back-compat)")
    return _master_secret()


# ── Mythos owner-key HMAC ──────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_mythos_hmac_secret() -> bytes:
    """Return the bytes used as the HMAC key for the Mythos owner key.

    Reads `MYTHOS_HMAC_SECRET`; falls back to `JWT_SECRET`.
    """
    dedicated = os.environ.get("MYTHOS_HMAC_SECRET", "").strip()
    if dedicated:
        logger.info("Mythos HMAC secret: dedicated (MYTHOS_HMAC_SECRET)")
        return dedicated.encode()
    logger.info("Mythos HMAC secret: derived from JWT_SECRET (back-compat)")
    return _master_secret().encode()


# ── Fernet ─────────────────────────────────────────────────────────────────

def _coerce_fernet_key(raw: str) -> bytes:
    """Validate / shape a Fernet key.

    Accepts either:
      - a 32-byte urlsafe-base64-encoded string (44 chars with `=` padding,
        which is the canonical Fernet key format), or
      - any other secret, in which case we derive a Fernet key by
        sha256-hashing then urlsafe-base64-encoding (matches the
        legacy derivation in `auth/encryption.py`).

    Returns the 44-char base64 key as bytes.
    """
    raw_b = raw.encode() if isinstance(raw, str) else raw
    # Canonical Fernet key: 44 chars urlsafe base64 → 32 raw bytes.
    if len(raw_b) == 44:
        try:
            decoded = base64.urlsafe_b64decode(raw_b)
            if len(decoded) == 32:
                return raw_b
        except Exception:
            pass
    # Otherwise hash-derive to get a deterministic 32 bytes, then encode.
    return base64.urlsafe_b64encode(hashlib.sha256(raw_b).digest())


@lru_cache(maxsize=1)
def get_primary_fernet_key() -> bytes:
    """Primary Fernet key — used for new encrypts AND decrypts.

    Reads `FERNET_KEY`; falls back to sha256(JWT_SECRET).
    """
    dedicated = os.environ.get("FERNET_KEY", "").strip()
    if dedicated:
        logger.info("Fernet primary key: dedicated (FERNET_KEY)")
        return _coerce_fernet_key(dedicated)
    logger.info("Fernet primary key: derived from JWT_SECRET (back-compat)")
    return _coerce_fernet_key(_master_secret())


@lru_cache(maxsize=1)
def get_fernet_secondary_keys() -> list[bytes]:
    """Secondary Fernet keys — decrypt-only (rotation overlap window).

    Reads `FERNET_KEYS_OLD` as comma-separated list. Each entry
    follows the same coercion rules as the primary key. Returns
    an empty list when the env var is unset (no overlap → only
    the primary key is in play).

    Use during a key rotation: set `FERNET_KEYS_OLD=<previous-key>`
    on the same deploy that promotes a new `FERNET_KEY`. New writes
    use the new primary; old ciphertexts decrypt via the secondary
    list. After re-encryption migration completes, clear the env
    var to drop the old key from the trust set.
    """
    raw = os.environ.get("FERNET_KEYS_OLD", "").strip()
    if not raw:
        return []
    keys = []
    for entry in raw.split(","):
        entry = entry.strip()
        if entry:
            keys.append(_coerce_fernet_key(entry))
    if keys:
        logger.info("Fernet secondary keys: %d loaded (rotation overlap)", len(keys))
    return keys


# ── boot-time fingerprint emission (paired with main.py A-03) ──────────────

def boot_fingerprints() -> dict[str, str]:
    """Return sha256[:16] fingerprints of each derived secret.

    Operators diff this output across deploys to verify rotations.
    No secret is included in the return — only its 16-char digest.
    """
    def fp(material: bytes | str) -> str:
        b = material.encode() if isinstance(material, str) else material
        return hashlib.sha256(b).hexdigest()[:16]

    return {
        "jwt_signing": fp(get_jwt_signing_secret()),
        "mythos_hmac": fp(get_mythos_hmac_secret()),
        "fernet_primary": fp(get_primary_fernet_key()),
        "fernet_secondary_count": str(len(get_fernet_secondary_keys())),
    }
