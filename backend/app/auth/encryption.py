"""Simple API key encryption using HMAC-based obfuscation.

Uses the JWT_SECRET as the encryption key. This is NOT cryptographically
perfect (no IV, deterministic) but prevents plaintext key exposure in DB
dumps while keeping the implementation dependency-free (no cryptography lib).

For production: upgrade to Fernet (cryptography package) or a KMS.
"""

import base64
import hashlib
import hmac
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_KEY = settings.jwt_secret.encode()[:32]


def encrypt_api_key(plaintext: str) -> str:
    """Obfuscate an API key for DB storage. Reversible with decrypt_api_key()."""
    if not plaintext:
        return ""
    # XOR with HMAC-derived key stream
    key_stream = hmac.new(_KEY, b"nexusforge-key-encrypt", hashlib.sha256).digest()
    plaintext_bytes = plaintext.encode()
    encrypted = bytes(b ^ key_stream[i % len(key_stream)] for i, b in enumerate(plaintext_bytes))
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_api_key(encrypted: str) -> str:
    """Recover an API key from its encrypted form."""
    if not encrypted:
        return ""
    try:
        encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode())
        key_stream = hmac.new(_KEY, b"nexusforge-key-encrypt", hashlib.sha256).digest()
        decrypted = bytes(b ^ key_stream[i % len(key_stream)] for i, b in enumerate(encrypted_bytes))
        return decrypted.decode()
    except Exception as exc:
        logger.warning("Failed to decrypt API key: %s", exc)
        return ""
