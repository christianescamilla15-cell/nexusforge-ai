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

H-2 Phase 1 (2026-04-27): primary Fernet key now sourced from the
dedicated `FERNET_KEY` env var (with `JWT_SECRET` fallback) via
`app.auth.secrets.get_primary_fernet_key()`.

H-2 Phase 2 (2026-04-27): when `FERNET_KEYS_OLD` is set, the global
`fernet:` handler upgrades to `MultiFernet` — new encrypts use the
primary, decrypts try primary then each secondary in order. Lets
operators rotate `FERNET_KEY` without bricking existing rows: keep
the previous key in `FERNET_KEYS_OLD`, deploy the new key, run the
re-encryption migration (Phase 4), then drop the secondary.

The per-tenant `tfernet:` path still uses a single IKM
(`jwt_secret`) — overlap-rotation for per-tenant keys is a separate
M-10 followup tracked in the runbook. For now, rotating the
master IKM that backs `_derive_tenant_fernet` requires a full
re-encryption pass (no overlap).

Cipher prefix taxonomy:
  - `tfernet:`  per-tenant Fernet (M-10, single IKM today)
  - `fernet:`   global Fernet, MultiFernet-aware (H-2 Phase 2)
  - bare base64 XOR (very legacy, pre-Fernet rollout)
"""

import base64
import hashlib
import hmac
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Legacy XOR derivation key — preserved as-is so existing
# (very-back-compat) XOR ciphertexts still decrypt. JWT_SECRET[:32]
# is documented sloppy (UTF-8 truncation edge case, L-1) but
# changing it would brick those rows. Re-encrypt out of band if
# needed.
_KEY = settings.jwt_secret.encode()[:32]

# H-2 Phase 1 (2026-04-27): primary Fernet key now sourced from
# `app.auth.secrets.get_primary_fernet_key()`, which reads
# `FERNET_KEY` if set or falls back to sha256(JWT_SECRET) (matching
# the legacy derivation). The legacy `_FERNET_KEY` constant is gone
# — call `_primary_fernet_bytes()` instead so a rotation that
# clears the lru_cache picks up the new key without re-import.

_fernet = None


def _primary_fernet_bytes() -> bytes:
    from app.auth.secrets import get_primary_fernet_key
    return get_primary_fernet_key()


def _secondary_fernet_keys() -> list[bytes]:
    from app.auth.secrets import get_fernet_secondary_keys
    return get_fernet_secondary_keys()


def reset_fernet_cache() -> None:
    """Drop the cached MultiFernet so a runtime env-var change (or
    test monkeypatch) takes effect on the next encrypt/decrypt."""
    global _fernet
    _fernet = None


def _get_fernet():
    """Return the global Fernet handler.

    H-2 Phase 2 (2026-04-27): when `FERNET_KEYS_OLD` is set, returns
    a `MultiFernet([primary, *secondary])` — primary signs new
    encrypts, every key is tried for decrypt. This is the overlap
    window during a `FERNET_KEY` rotation: keep the previous key in
    `FERNET_KEYS_OLD` until all stored ciphertexts have been
    re-encrypted with the new primary, then drop it.

    With no secondaries, behavior is identical to the pre-Phase-2
    single-Fernet path (back-compat for non-rotating deploys).
    """
    global _fernet
    if _fernet is None:
        try:
            from cryptography.fernet import Fernet, MultiFernet
            primary = Fernet(_primary_fernet_bytes())
            secondary = [Fernet(k) for k in _secondary_fernet_keys()]
            if secondary:
                _fernet = MultiFernet([primary, *secondary])
                logger.info(
                    "Fernet handler: MultiFernet with %d secondary key(s) for rotation overlap",
                    len(secondary),
                )
            else:
                _fernet = primary
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
