"""Google OAuth2 — verifies Google id_token using Google's tokeninfo endpoint."""

import logging
import os
import httpx

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


async def verify_google_token(id_token: str) -> dict | None:
    """Verify a Google id_token and return user info, or None if invalid."""
    if not id_token:
        return None

    # Use Google's tokeninfo endpoint — no extra library needed
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
            )
        if resp.status_code != 200:
            logger.warning("Google tokeninfo returned status %s", resp.status_code)
            return None

        data = resp.json()

        # Verify the token was issued for our app
        aud = data.get("aud", "")
        if GOOGLE_CLIENT_ID and aud != GOOGLE_CLIENT_ID:
            logger.warning("Google token audience mismatch")
            return None

        email = data.get("email")
        if not email:
            return None

        return {
            "sub": data.get("sub"),
            "email": email,
            "name": data.get("name") or email.split("@")[0],
            "picture": data.get("picture"),
            "email_verified": data.get("email_verified") == "true",
        }

    except Exception as exc:
        logger.error("verify_google_token failed: %s", type(exc).__name__)
        return None
