"""JWT token creation and verification with role-based claims.

H-2 partial (2026-04-25): tokens now carry a `jti` (JWT ID) so they
can be individually revoked via `app.auth.revocation.revoke_jti`.
The full retro recommendation (split JWT_SECRET into 3 secrets,
introduce refresh tokens) is deferred to a focused session — this
commit ships the immediate "I leaked a token, revoke it" capability
without breaking active sessions or touching Fernet.
"""
import secrets
import time

import jwt

from app.config import settings

SECRET = settings.jwt_secret
ALGORITHM = 'HS256'
TOKEN_EXPIRY = 3600 * 8  # 8 hours


def create_token(user_id: str, email: str, role: str = 'member') -> str:
    """Issue a signed JWT with a fresh jti claim."""
    now = int(time.time())
    payload = {
        'sub': user_id,
        'email': email,
        'role': role,
        'iat': now,
        'exp': now + TOKEN_EXPIRY,
        # H-2: jti is a 128-bit URL-safe random — used by
        # app.auth.revocation to invalidate this specific token.
        'jti': secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Decode + signature-verify. Returns None on bad / expired tokens.

    Note: revocation check is intentionally NOT here. Many call sites
    are sync and the revocation list is async (Redis). Async callers
    should `await app.auth.revocation.is_jti_revoked(claims['jti'])`
    before trusting the token. Sync callers (the existing middleware
    + helpers) keep working unchanged — they get signature + exp
    verification only, and the revocation layer is defense-in-depth.
    """
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_role(token_data: dict) -> str:
    return token_data.get('role', 'viewer')
