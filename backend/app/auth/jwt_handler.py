"""JWT token creation and verification with role-based claims.

H-2 partial (2026-04-25): tokens carry a `jti` (JWT ID) so they can
be individually revoked via `app.auth.revocation.revoke_jti`.

H-2 Phase 1 (2026-04-27): signing secret comes from
`app.auth.secrets.get_jwt_signing_secret()`, which reads
`JWT_SIGNING_SECRET` if set or falls back to `JWT_SECRET`. The
master `JWT_SECRET` is no longer referenced directly here, so a
future commit can drop its required-at-boot status without touching
this file.
"""
import secrets as _secrets
import time

import jwt

from app.auth.secrets import get_jwt_signing_secret

ALGORITHM = 'HS256'
TOKEN_EXPIRY = 3600 * 8  # 8 hours — see ACCESS_TOKEN_EXPIRY notes for the
                        # forthcoming refresh-token split (Phase 3).


def _signing_secret() -> str:
    # Indirection lets tests / runtime rotate without re-importing.
    return get_jwt_signing_secret()


# Back-compat: external callers and existing tests historically
# imported `SECRET` from this module to encode/sign tokens directly.
# Resolved at import time — sufficient for tests and for any caller
# that doesn't need rotation-during-request semantics. New code should
# call `_signing_secret()` instead.
SECRET = _signing_secret()


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
        'jti': _secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, _signing_secret(), algorithm=ALGORITHM)


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
        return jwt.decode(token, _signing_secret(), algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_role(token_data: dict) -> str:
    return token_data.get('role', 'viewer')
