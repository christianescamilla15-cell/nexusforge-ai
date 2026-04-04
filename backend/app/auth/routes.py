"""Auth routes — register, login, Google OAuth, profile."""

import bcrypt
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from .jwt_handler import create_token, verify_token
from ..db.client import get_db_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Models ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleLoginRequest(BaseModel):
    id_token: str

class TokenResponse(BaseModel):
    token: str
    user: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash. Supports bcrypt and legacy SHA-256."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, Exception):
        # Fallback: check legacy SHA-256 hash (pre-bcrypt migration)
        import hashlib
        if hashlib.sha256(password.encode()).hexdigest() == password_hash:
            return True  # Legacy match — caller should re-hash
        return False


async def _rehash_if_legacy(email: str, password: str, password_hash: str):
    """If password was verified via legacy SHA-256, upgrade to bcrypt."""
    try:
        bcrypt.checkpw(password.encode(), password_hash.encode())
        return  # Already bcrypt, no action needed
    except (ValueError, Exception):
        # Legacy hash — upgrade to bcrypt
        new_hash = _hash_password(password)
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE nf_users SET password_hash = $1 WHERE email = $2",
                new_hash, email,
            )


async def _get_or_create_user(email: str, name: str = None, provider: str = "email",
                               provider_id: str = None, password_hash: str = None) -> dict:
    """Get existing user or create new one. Returns user dict."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Check existing
        row = await conn.fetchrow("SELECT * FROM nf_users WHERE email = $1", email)
        if row:
            return dict(row)

        # Create new
        row = await conn.fetchrow(
            """INSERT INTO nf_users (email, name, provider, provider_id, password_hash)
               VALUES ($1, $2, $3, $4, $5) RETURNING *""",
            email, name or email.split("@")[0], provider, provider_id, password_hash,
        )
        logger.info("New user created: %s (%s)", email, provider)
        return dict(row)


def _user_to_safe(user: dict) -> dict:
    """Strip sensitive fields from user dict."""
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "plan": user["plan"],
        "runs_today": user["runs_today"],
        "created_at": user["created_at"].isoformat() if user.get("created_at") else None,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """Register with email + password."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM nf_users WHERE email = $1", req.email)
        if existing:
            raise HTTPException(409, "Email already registered")

    user = await _get_or_create_user(
        email=req.email,
        name=req.name,
        provider="email",
        password_hash=_hash_password(req.password),
    )
    token = create_token(str(user["id"]), user["email"], user["role"])
    return {"token": token, "user": _user_to_safe(user)}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Login with email + password."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM nf_users WHERE email = $1", req.email)

    if not user:
        raise HTTPException(401, "Invalid email or password")
    if not user["password_hash"] or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    if not user["is_active"]:
        raise HTTPException(403, "Account disabled")

    # Auto-migrate legacy SHA-256 passwords to bcrypt
    await _rehash_if_legacy(req.email, req.password, user["password_hash"])

    token = create_token(str(user["id"]), user["email"], user["role"])
    return {"token": token, "user": _user_to_safe(dict(user))}


@router.post("/google", response_model=TokenResponse)
async def google_login(req: GoogleLoginRequest):
    """Login with Google OAuth token."""
    from .oauth import verify_google_token
    google_user = await verify_google_token(req.id_token)
    if not google_user:
        raise HTTPException(401, "Invalid Google token")

    user = await _get_or_create_user(
        email=google_user["email"],
        name=google_user.get("name"),
        provider="google",
        provider_id=google_user["sub"],
    )
    token = create_token(str(user["id"]), user["email"], user["role"])
    return {"token": token, "user": _user_to_safe(user)}


@router.get("/me")
async def get_me(request: Request):
    """Get current user from JWT token."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")

    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid or expired token")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM nf_users WHERE id = $1::uuid", token_data["sub"])

    if not user:
        raise HTTPException(404, "User not found")

    return _user_to_safe(dict(user))


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, request: Request):
    """Change password for the authenticated user."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    data = verify_token(auth[7:])
    if not data:
        raise HTTPException(401, "Invalid token")

    user_id = data.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token")

    if len(body.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT password_hash FROM nf_users WHERE id = $1::uuid", user_id)
        if not row:
            raise HTTPException(404, "User not found")

        if not _verify_password(body.current_password, row["password_hash"]):
            raise HTTPException(400, "Current password is incorrect")

        new_hash = _hash_password(body.new_password)
        await conn.execute(
            "UPDATE nf_users SET password_hash = $1 WHERE id = $2::uuid",
            new_hash, user_id,
        )

    return {"changed": True}


@router.get("/plans")
async def get_plans():
    """List available plans with limits."""
    return {
        "plans": [
            {"id": "free", "name": "Free", "price": 0, "runs_per_day": 5, "agents": 3, "features": ["Basic workflows", "Email notifications"]},
            {"id": "pro", "name": "Pro", "price": 29, "runs_per_day": 100, "agents": 22, "features": ["All agents", "6 topologies", "API key", "Priority support"]},
            {"id": "team", "name": "Team", "price": 99, "runs_per_day": 500, "agents": 22, "features": ["Custom agents", "Slack integration", "5 seats", "Audit logs"]},
            {"id": "enterprise", "name": "Enterprise", "price": None, "runs_per_day": -1, "agents": 43, "features": ["Unlimited", "SSO", "Self-hosted", "SLA", "Dedicated support"]},
        ]
    }
