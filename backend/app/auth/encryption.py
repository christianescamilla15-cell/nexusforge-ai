"""API key encryption — Fernet symmetric encryption (AES-128-CBC + HMAC).

Uses the first 32 bytes of JWT_SECRET as the Fernet key base.
Each encryption uses a unique IV (non-deterministic).
Backwards-compatible: tries Fernet first, falls back to legacy XOR decryption.
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
    """Encrypt an API key for DB storage. Uses Fernet (AES) if available, falls back to XOR."""
    if not plaintext:
        return ""
    f = _get_fernet()
    if f:
        return "fernet:" + f.encrypt(plaintext.encode()).decode()
    # Legacy XOR fallback
    return _xor_encrypt(plaintext)


def decrypt_api_key(encrypted: str) -> str:
    """Decrypt an API key. Auto-detects Fernet vs legacy XOR format."""
    if not encrypted:
        return ""
    try:
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
