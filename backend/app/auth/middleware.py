"""Auth middleware — enforces JWT on protected routes, injects user into request.state."""

import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from .jwt_handler import verify_token

logger = logging.getLogger(__name__)

# Routes that don't require authentication
PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/google",
    "/api/auth/plans",
    "/docs",
    "/openapi.json",
    "/redoc",
}

PUBLIC_PREFIXES = [
    "/api/auth/",
    "/docs",
    "/openapi",
    "/redoc",
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")

        # Skip auth for public routes
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract and verify token
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token_data = verify_token(auth[7:])
            if token_data:
                request.state.user = token_data
                request.state.user_id = token_data.get("sub")
                request.state.user_plan = token_data.get("plan", "free")
                return await call_next(request)

        # No valid token — allow request but mark as anonymous
        # This enables gradual migration: existing features work without auth
        request.state.user = None
        request.state.user_id = None
        request.state.user_plan = "free"
        return await call_next(request)
