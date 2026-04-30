"""Auth middleware — enforces JWT on protected routes, injects user into request.state."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .jwt_handler import verify_token

logger = logging.getLogger(__name__)

# Routes that don't require authentication
PUBLIC_PATHS = {
    "/api/health",
    "/api/health/ready",  # K8s/Render readiness probe — added 2026-04-30 (Tier 4 #7)
    "/api/ping",          # Lightweight liveness probe (no DB/Redis touch)
    "/api/version",       # Build info — used by frontend for cache-bust + by uptime checks
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/google",
    "/api/auth/plans",
    "/api/integrations/status",
}

# H-4 (2026-04-25): each entry MUST be the canonical namespace root
# **without** a trailing slash. A request matches when its path equals
# the entry exactly OR starts with `entry + "/"`. Substring `startswith`
# was the prior bug — `/api/mythos` would otherwise also exempt
# `/api/mythos-internal`, and `/api/refactor/showcase` would exempt
# `/api/refactor/showcase-debug`. The new helper below enforces a
# real path-segment boundary.
PUBLIC_PREFIXES = [
    "/api/auth",
    "/api/templates",
    "/api/automations/webhook",
    "/api/mythos",            # Self-protected via X-Mythos-Key (returns 404 without it)
    "/api/refactor/showcase",  # Public read-only demo reports (static JSON)
    "/api/v1/refactor/showcase",
]

# Swagger/docs: always available, auth-protected in production
# In development: public (no auth needed)
# In production: requires valid JWT token (same as other protected routes)
import os as _os
if _os.environ.get("NEXUSFORGE_ENV", "development") != "production":
    PUBLIC_PATHS.update({"/docs", "/openapi.json", "/redoc"})
    PUBLIC_PREFIXES.extend(["/docs", "/openapi", "/redoc"])
# In production, /docs requires auth — handled by AuthMiddleware (not in PUBLIC_PATHS)


def _is_public(path: str) -> bool:
    """Return True iff `path` is exempt from JWT auth.

    Public when either:
      - exact match against `PUBLIC_PATHS` (small set of single endpoints), or
      - exact match OR proper child of any entry in `PUBLIC_PREFIXES`.

    Proper child = `path == prefix OR path.startswith(prefix + "/")`.
    A bare `path.startswith(prefix)` is unsafe because `/api/mythos`
    would also match `/api/mythos-internal` — see H-4 in the
    2026-04-25 retro.
    """
    if path in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")

        # Skip auth for public routes
        if _is_public(path):
            request.state.user = None
            request.state.user_id = None
            request.state.user_plan = "free"
            return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract and verify token
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token_data = verify_token(auth[7:])
            if token_data:
                # H-2 (2026-04-25): refuse explicitly-revoked tokens.
                # Fail-open on Redis errors (see revocation.py rationale).
                jti = token_data.get("jti")
                if jti:
                    from .revocation import is_jti_revoked
                    if await is_jti_revoked(jti):
                        return JSONResponse(
                            status_code=401,
                            content={"detail": "Token revoked"},
                        )
                request.state.user = token_data
                request.state.user_id = token_data.get("sub")
                request.state.user_plan = token_data.get("plan", "free")
                return await call_next(request)

        # No valid token — BLOCK access to protected routes
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
        )
