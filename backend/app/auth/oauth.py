"""Google OAuth2 — verifies Google id_token using the google-auth library.

H-1 (2026-04-25): replaced the deprecated tokeninfo HTTP endpoint with
`google.oauth2.id_token.verify_oauth2_token`, which:

- Verifies the id_token's RS256 signature locally against Google's
  published JWKs (cached in-process). No outbound HTTP per request,
  no chance of an attacker MITM-ing a tokeninfo response.
- Validates the issuer (`accounts.google.com` / `https://accounts.google.com`).
- Validates audience (`aud`) against `GOOGLE_CLIENT_ID`.
- Validates expiration (`exp`) automatically.

A jti / nonce-based replay-protection layer (Redis with TTL = id_token
lifetime) is the next step under H-2 (full JWT lifecycle work) and is
not included here — that work depends on an audit of every
`auth/*` flow that issues a NexusForge JWT.
"""

import logging
import os

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# Reuse a single transport across calls — the JWK cache lives on it.
_TRANSPORT = google_requests.Request()


async def verify_google_token(id_token: str) -> dict | None:
    """Verify a Google id_token and return user info, or None if invalid."""
    if not id_token:
        return None
    if not GOOGLE_CLIENT_ID:
        logger.error("verify_google_token called but GOOGLE_CLIENT_ID is not set")
        return None

    try:
        # Synchronous CPU work — JWK signature verify takes ~1ms when
        # the JWK cache is warm. Acceptable inside the request handler;
        # if it ever becomes a hotspot, wrap in `run_in_executor`.
        claims = google_id_token.verify_oauth2_token(
            id_token,
            _TRANSPORT,
            audience=GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        # `verify_oauth2_token` raises ValueError on signature mismatch,
        # bad issuer, expired token, audience mismatch.
        logger.warning("Google id_token verification failed: %s", exc)
        return None
    except Exception:
        # Defensive: any other unexpected error is logged with type only.
        logger.exception("verify_google_token unexpected error")
        return None

    # Issuer must be one of Google's two canonical strings; the library
    # already enforces this, but defense-in-depth — refuse anything
    # else explicitly.
    iss = claims.get("iss", "")
    if iss not in ("accounts.google.com", "https://accounts.google.com"):
        logger.warning("Google id_token issuer mismatch: %r", iss)
        return None

    email = claims.get("email")
    if not email:
        return None

    return {
        "sub": claims.get("sub"),
        "email": email,
        "name": claims.get("name") or email.split("@")[0],
        "picture": claims.get("picture"),
        # `email_verified` is a real bool from google-auth (was a string
        # "true"/"false" in the deprecated tokeninfo response).
        "email_verified": bool(claims.get("email_verified", False)),
    }
