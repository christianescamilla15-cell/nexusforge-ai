"""API key encryption — Fernet symmetric encryption (AES-128-CBC + HMAC).

Uses the first 32 bytes of JWT_SECRET as the Fernet key base.
Each encryption uses a unique IV (non-deterministic).
Backwards-compatible: tries Fernet first, falls back to legacy XOR decryption.

M-10 (2026-04-25): added per-tenant Fernet derivation via HKDF.
`encrypt_api_key_for_tenant(plaintext, tenant_id)` and the matching
`decrypt_api_key_for_tenant(...)` derive a unique Fernet key per
tenant (`HKDF(jwt_secret, salt=tenant_id, info="api-keys")`). New
writes should use the per-tenant variants; the legacy global-key
functions stay for backwards compatibility (they're still the
fallback decrypt path).

Cipher prefix taxonomy:
  - `tfernet:`  per-tenant Fernet (new, M-10)
  - `fernet:`   global Fernet (legacy)
  - bare base64 XOR (very legacy, pre-Fernet rollout)
"""

import base64
import hashlib
import hmac
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_KEY = settings.jwt_secret.encode()[:32]

# Derive a proper Fernet key (32 bytes, base64-encoded = 44 chars)
_FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(_KEY).digest())

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is None:
        try:
            from cryptography.fernet import Fernet
            _fernet = Fernet(_FERNET_KEY)
        except ImportError:
            logger.warning("cryptography package not installed — using legacy XOR encryption")
            _fernet = False  # Sentinel: unavailable
    return _fernet


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key for DB storage. Uses Fernet (AES) if available, falls back to XOR.

    DEPRECATED (M-10, 2026-04-25): prefer
    `encrypt_api_key_for_tenant(plaintext, tenant_id)` so a DB dump
    cannot be decrypted en masse with the single global key.
    """
    if not plaintext:
        return ""
    f = _get_fernet()
    if f:
        return "fernet:" + f.encrypt(plaintext.encode()).decode()
    # Legacy XOR fallback
    return _xor_encrypt(plaintext)


def decrypt_api_key(encrypted: str) -> str:
    """Decrypt an API key. Auto-detects per-tenant / Fernet / legacy XOR format.

    Prefer `decrypt_api_key_for_tenant(encrypted, tenant_id)` —
    this function only handles the legacy global-key formats.
    `tfernet:`-prefixed values raise an error here because they
    require the tenant_id at decrypt time.
    """
    if not encrypted:
        return ""
    try:
        if encrypted.startswith("tfernet:"):
            logger.error(
                "decrypt_api_key called on per-tenant cipher; use "
                "decrypt_api_key_for_tenant(...) instead"
            )
            return ""
        if encrypted.startswith("fernet:"):
            f = _get_fernet()
            if not f:
                logger.error("Cannot decrypt Fernet-encrypted key: cryptography package not installed")
                return ""
            return f.decrypt(encrypted[7:].encode()).decode()
        # Legacy XOR format (backwards compatibility)
        return _xor_decrypt(encrypted)
    except Exception as exc:
        logger.warning("Failed to decrypt API key: %s", exc)
        return ""


# ── M-10: per-tenant Fernet via HKDF ────────────────────────────────────────

def _derive_tenant_fernet(tenant_id: str):
    """HKDF(jwt_secret, salt=tenant_id, info='api-keys') → Fernet key.

    Each tenant gets a key that is computationally isolated from
    every other tenant's, so a DB dump no longer == universal
    decrypt. The master `JWT_SECRET` is still the input keying
    material — rotating it still requires re-encryption (see
    `docs/runbooks/key-rotation.md`).
    """
    try:
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        from cryptography.fernet import Fernet
    except ImportError:
        logger.error("cryptography package not installed — cannot derive tenant Fernet")
        return None
    if not tenant_id:
        logger.error("tenant_id required for per-tenant Fernet derivation")
        return None

    raw = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=tenant_id.encode(),
        info=b"nexusforge-api-keys-v1",
    ).derive(settings.jwt_secret.encode())
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_api_key_for_tenant(plaintext: str, tenant_id: str) -> str:
    """Encrypt with a per-tenant Fernet key. Output prefixed `tfernet:`.

    Falls back to `encrypt_api_key` (global key) only if the tenant
    derivation cannot run (cryptography missing, empty tenant_id).
    """
    if not plaintext:
        return ""
    f = _derive_tenant_fernet(tenant_id)
    if f is None:
        # Defensive fallback so callers never crash; observability
        # via the warning logged inside _derive_tenant_fernet.
        return encrypt_api_key(plaintext)
    return "tfernet:" + f.encrypt(plaintext.encode()).decode()


def decrypt_api_key_for_tenant(encrypted: str, tenant_id: str) -> str:
    """Decrypt per-tenant or legacy-format ciphertext.

    Routing:
      - `tfernet:...` → per-tenant Fernet (requires tenant_id).
      - `fernet:...`  → legacy global Fernet (back-compat).
      - bare base64   → legacy XOR (very-back-compat).
    """
    if not encrypted:
        return ""
    try:
        if encrypted.startswith("tfernet:"):
            f = _derive_tenant_fernet(tenant_id)
            if f is None:
                return ""
            return f.decrypt(encrypted[8:].encode()).decode()
        # Falls through to global / legacy paths.
        return decrypt_api_key(encrypted)
    except Exception as exc:
        logger.warning("Failed to decrypt per-tenant API key: %s", type(exc).__name__)
        return ""


# ── Legacy XOR (backwards compatibility only) ───────────────────────────────

def _xor_encrypt(plaintext: str) -> str:
    key_stream = hmac.new(_KEY, b"nexusforge-key-encrypt", hashlib.sha256).digest()
    plaintext_bytes = plaintext.encode()
    encrypted = bytes(b ^ key_stream[i % len(key_stream)] for i, b in enumerate(plaintext_bytes))
    return base64.urlsafe_b64encode(encrypted).decode()


def _xor_decrypt(encrypted: str) -> str:
    encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode())
    key_stream = hmac.new(_KEY, b"nexusforge-key-encrypt", hashlib.sha256).digest()
    decrypted = bytes(b ^ key_stream[i % len(key_stream)] for i, b in enumerate(encrypted_bytes))
    return decrypted.decode()
