"""Auth routes — register, login, Google OAuth, profile."""

import bcrypt
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from .jwt_handler import (
    create_token, verify_token,
    ACCESS_TOKEN_EXPIRY_SHORT,
)
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
    """Register with email + password. Sends verification code via email."""
    from app.auth.codes import create_code

    # M-2 (2026-04-25): bumped from 6 to 12 chars to clear NIST 800-63B
    # baseline (8+) with a margin. No composition rules — length is
    # the only entropy lever that matters.
    if len(req.password) < 12:
        raise HTTPException(400, "Password must be at least 12 characters")

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

    # Send verification code (stored in DB, shared across workers)
    code = await create_code(req.email, "verify")
    try:
        from app.integrations.email.client import send_email
        await send_email(
            to=req.email,
            subject="NexusForge — Verify your email",
            html=f"<h2>Your verification code: <strong>{code}</strong></h2><p>Enter this code in NexusForge to verify your account.</p>",
        )
    except Exception as exc:
        logger.warning("Verification email failed: %s", exc)

    resp = await _issue_login_response(user)
    resp["needs_verification"] = True
    return resp


class VerifyEmailRequest(BaseModel):
    email: str
    code: str

@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest):
    """Verify email with 6-digit code (stored in DB, shared across workers)."""
    from app.auth.codes import verify_code
    valid = await verify_code(body.email, "verify", body.code)
    if not valid:
        raise HTTPException(400, "Invalid or expired verification code")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE nf_users SET email_verified = true WHERE email = $1",
            body.email,
        )
    return {"verified": True}


# M-2 (2026-04-25): per-IP login throttle. /auth/login lives in
# PUBLIC_PREFIXES so the per-user `check_rate_limit` doesn't apply
# pre-auth — credential stuffing was wide open. We add a lightweight
# Redis counter keyed by client IP. Fail-open if Redis is down so a
# Redis blip doesn't lock everyone out.
_LOGIN_MAX_ATTEMPTS = 10        # per IP
_LOGIN_WINDOW_SECONDS = 60 * 5  # 5 minutes


# H-2 Phase 3 (2026-04-27): refresh-token feature flag. Default OFF
# so existing deploys keep issuing the legacy 8h JWTs unchanged. Set
# `ENABLE_REFRESH_TOKENS=true` (or 1/yes) to opt this deployment into
# the short-access + refresh model. Frontend must learn to call
# /auth/refresh BEFORE this flag is flipped on.
def _refresh_tokens_enabled() -> bool:
    return os.environ.get("ENABLE_REFRESH_TOKENS", "").strip().lower() in ("true", "1", "yes")


async def _issue_login_response(user: dict) -> dict:
    """Build the response body returned by login / register / google.

    Always returns `{token, user}`. When `ENABLE_REFRESH_TOKENS` is
    on, also returns `{refresh_token, expires_in}` and shortens the
    access token TTL to 15 minutes. Backwards-compatible — clients
    that don't know about refresh_token simply ignore the extra
    field.
    """
    user_id = str(user["id"])
    email = user["email"]
    role = user["role"]

    if _refresh_tokens_enabled():
        access = create_token(user_id, email, role, expires_in=ACCESS_TOKEN_EXPIRY_SHORT)
        from .refresh import issue_refresh_token, REFRESH_TTL_SECONDS
        from .tenant import lookup_user_org
        org_id = await lookup_user_org(user_id)
        refresh = await issue_refresh_token(user_id, email, role, org_id=org_id)
        if refresh is None:
            # Redis down → can't issue a refresh token. Fall back to
            # an 8h access token so the user can still log in, but
            # surface the degraded state in logs.
            logger.warning(
                "Refresh tokens enabled but Redis unavailable; falling back to 8h access token for user=%s",
                user_id[:8],
            )
            return {"token": create_token(user_id, email, role), "user": _user_to_safe(user)}
        return {
            "token": access,
            "refresh_token": refresh,
            "expires_in": ACCESS_TOKEN_EXPIRY_SHORT,
            "refresh_expires_in": REFRESH_TTL_SECONDS,
            "user": _user_to_safe(user),
        }

    # Legacy single-token path.
    return {"token": create_token(user_id, email, role), "user": _user_to_safe(user)}


async def _check_login_rate_limit(client_ip: str) -> None:
    if not client_ip:
        return
    try:
        from app.db.client import get_redis
        r = await get_redis()
        if r is None:
            return
        key = f"nf:login_rate:{client_ip}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, _LOGIN_WINDOW_SECONDS)
        if count > _LOGIN_MAX_ATTEMPTS:
            raise HTTPException(429, "Too many login attempts; try again later")
    except HTTPException:
        raise
    except Exception:
        # Don't take down auth on a Redis blip.
        return


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request):
    """Login with email + password."""
    # Per-IP throttle — see _check_login_rate_limit comment above.
    client_ip = (request.client.host if request.client else "") or ""
    await _check_login_rate_limit(client_ip)

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

    return await _issue_login_response(dict(user))


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
    return await _issue_login_response(user)


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_access_token(body: RefreshRequest):
    """Exchange a refresh token for a new access + refresh pair.

    H-2 Phase 3 (2026-04-27). Single-use semantics: the submitted
    refresh token is revoked atomically as part of the lookup, so a
    replay (legitimate or attacker) hits an empty key. The response
    carries a fresh access JWT (15min) and a NEW refresh token
    (7d) — the client must persist the new refresh token and
    discard the old one.

    Returns 503 when `ENABLE_REFRESH_TOKENS` is off so misconfigured
    clients fail loudly instead of silently accepting an empty
    response. Returns 401 on any invalid/expired/revoked token.
    """
    if not _refresh_tokens_enabled():
        raise HTTPException(503, "Refresh tokens are not enabled on this deployment")

    from .refresh import consume_refresh_token, issue_refresh_token, REFRESH_TTL_SECONDS

    claims = await consume_refresh_token(body.refresh_token)
    if not claims:
        raise HTTPException(401, "Invalid or expired refresh token")

    user_id = claims["user_id"]
    email = claims["email"]
    role = claims.get("role", "member")
    # Preserve tenant context across rotation. Tokens issued before this
    # change won't have org_id — fall back to a fresh lookup so the new
    # token gets the claim populated rather than carrying None forward.
    org_id = claims.get("org_id")
    if org_id is None:
        from .tenant import lookup_user_org
        org_id = await lookup_user_org(user_id)

    new_access = create_token(user_id, email, role, expires_in=ACCESS_TOKEN_EXPIRY_SHORT)
    new_refresh = await issue_refresh_token(user_id, email, role, org_id=org_id)
    if new_refresh is None:
        # Redis flaked between consume and issue — return the new
        # access token but no refresh, so the client at least keeps
        # working until next access expiry. Caller can retry login.
        logger.warning("Refresh issue failed for user=%s; returning access-only", user_id[:8])
        return {
            "token": new_access,
            "expires_in": ACCESS_TOKEN_EXPIRY_SHORT,
            "refresh_token": None,
        }

    return {
        "token": new_access,
        "refresh_token": new_refresh,
        "expires_in": ACCESS_TOKEN_EXPIRY_SHORT,
        "refresh_expires_in": REFRESH_TTL_SECONDS,
    }


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/logout")
async def logout(request: Request, body: LogoutRequest | None = None):
    """Revoke the caller's JWT (H-2 partial, 2026-04-25).

    Adds the token's `jti` to the Redis revocation set with TTL =
    remaining token lifetime. After this returns 200, the token will
    be refused by `AuthMiddleware` even though it has not yet
    expired. Idempotent — calling twice is a no-op.

    H-2 Phase 3 (2026-04-27): if the request body carries a
    `refresh_token`, that refresh token is also revoked. Clients
    using the refresh-token model should always pass it on logout
    so the long-lived credential dies with the session.

    If Redis is unreachable the call returns 200 with
    `revoked=false` so the client doesn't surface a confusing error;
    operators should monitor for that field in logs.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")

    token_data = verify_token(auth[7:])

    # Revoke the refresh token first if provided — this is independent
    # of the access token's validity (the access token might already
    # be expired but the refresh is still live).
    refresh_revoked = False
    if body and body.refresh_token:
        from .refresh import revoke_refresh_token
        refresh_revoked = await revoke_refresh_token(body.refresh_token)

    if not token_data:
        return {
            "revoked": False,
            "refresh_revoked": refresh_revoked,
            "reason": "token-already-invalid",
        }

    jti = token_data.get("jti")
    exp = token_data.get("exp", 0)
    if not jti:
        return {
            "revoked": False,
            "refresh_revoked": refresh_revoked,
            "reason": "legacy-token-no-jti",
        }

    from .revocation import revoke_jti
    ok = await revoke_jti(jti, exp)
    return {"revoked": ok, "refresh_revoked": refresh_revoked}


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


@router.get("/export-data")
async def export_account_data(request: Request):
    """Export all user data as JSON (GDPR compliance)."""
    import json
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(401, "Invalid token")
    user_id = token_data["sub"]

    pool = await get_db_pool()
    automations = []
    workflows = []
    results_count = 0
    user = None
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM nf_users WHERE id = $1::uuid", user_id)
        try:
            automations = await conn.fetch("SELECT id, name, description, trigger_type, created_at FROM automations WHERE user_id = $1::uuid", user_id)
        except Exception:
            pass
        try:
            workflows = await conn.fetch("SELECT id, name, status, created_at FROM workflows WHERE user_id = $1::uuid", user_id)
        except Exception:
            pass
        try:
            results_count = await conn.fetchval("SELECT count(*) FROM automation_results WHERE user_id = $1::uuid", user_id)
        except Exception:
            pass

    return {
        "user": _user_to_safe(dict(user)) if user else {},
        "automations": [dict(a) for a in automations],
        "workflows": [dict(w) for w in workflows],
        "results_count": results_count or 0,
        "exported_at": __import__('time').strftime("%Y-%m-%dT%H:%M:%SZ", __import__('time').gmtime()),
    }


class DeleteAccountRequest(BaseModel):
    password: str
    confirmation: str = "DELETE"  # Must type "DELETE" to confirm


@router.post("/delete-account")
async def delete_account(body: DeleteAccountRequest, request: Request):
    """Permanently delete account and all associated data (GDPR right to erasure)."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    data = verify_token(auth[7:])
    if not data:
        raise HTTPException(401, "Invalid token")

    if body.confirmation != "DELETE":
        raise HTTPException(400, "Must confirm with 'DELETE'")

    user_id = data["sub"]
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Verify password
            user = await conn.fetchrow("SELECT password_hash FROM nf_users WHERE id = $1::uuid", user_id)
            if not user or not user["password_hash"]:
                raise HTTPException(404, "Account not found")

            import bcrypt
            if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
                raise HTTPException(401, "Invalid password")

            # Delete all user data (CASCADE handles most)
            await conn.execute("DELETE FROM automation_results WHERE automation_id IN (SELECT id FROM automations WHERE user_id = $1::uuid)", user_id)
            await conn.execute("DELETE FROM automations WHERE user_id = $1::uuid", user_id)
            await conn.execute("DELETE FROM workflows WHERE user_id = $1::uuid", user_id)
            await conn.execute("DELETE FROM workflow_runs WHERE user_id = $1::uuid", user_id)
            await conn.execute("DELETE FROM api_keys WHERE user_id = $1::uuid", user_id)
            await conn.execute("DELETE FROM agent_configs WHERE user_id = $1::uuid", user_id)
            await conn.execute("DELETE FROM audit_logs WHERE user_id = $1::uuid", user_id)
            await conn.execute("DELETE FROM nf_users WHERE id = $1::uuid", user_id)

        logger.info("Account deleted: %s", user_id[:8])
        return {"deleted": True, "message": "Account and all data permanently deleted"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "Internal server error")


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

        if not row["password_hash"]:
            raise HTTPException(400, "This account uses Google login — password cannot be changed here")

        if not _verify_password(body.current_password, row["password_hash"]):
            raise HTTPException(400, "Current password is incorrect")

        new_hash = _hash_password(body.new_password)
        await conn.execute(
            "UPDATE nf_users SET password_hash = $1 WHERE id = $2::uuid",
            new_hash, user_id,
        )

    return {"changed": True}


class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str

@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Send a 6-digit reset code (stored in DB, shared across workers)."""
    from app.auth.codes import create_code

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id, email FROM nf_users WHERE email = $1", body.email)

    if not user:
        return {"sent": True}

    code = await create_code(body.email, "reset")

    # Send via Resend (best-effort)
    try:
        from app.integrations.email.client import send_email
        await send_email(
            to=body.email,
            subject="NexusForge — Password Reset Code",
            html=f"<h2>Your reset code: <strong>{code}</strong></h2><p>This code expires in 15 minutes.</p>",
        )
    except Exception as exc:
        logger.warning("Failed to send reset email: %s", exc)

    return {"sent": True}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """Verify the 6-digit code (from DB) and set a new password."""
    from app.auth.codes import verify_code

    valid = await verify_code(body.email, "reset", body.code)
    if not valid:
        raise HTTPException(400, "Invalid or expired reset code")

    if len(body.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    new_hash = _hash_password(body.new_password)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE nf_users SET password_hash = $1 WHERE email = $2",
            new_hash, body.email,
        )
    if result == "UPDATE 0":
        raise HTTPException(404, "User not found")

    return {"reset": True}


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


class ConsentRequest(BaseModel):
    accepted_terms: bool = False
    accepted_privacy: bool = False
    accepted_marketing: bool = False


@router.post("/consent")
async def record_consent(body: ConsentRequest, request: Request):
    """Record user consent for Terms, Privacy, and Marketing (GDPR/LFPDPPP)."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    data = verify_token(auth[7:])
    if not data:
        raise HTTPException(401, "Invalid token")

    user_id = data["sub"]
    ip = request.client.host if request.client else ""
    ua = request.headers.get("User-Agent", "")[:500]

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            consents = [
                ("terms_of_service", body.accepted_terms),
                ("privacy_policy", body.accepted_privacy),
                ("marketing", body.accepted_marketing),
            ]
            for consent_type, accepted in consents:
                if accepted:
                    await conn.execute(
                        """INSERT INTO user_consents (user_id, consent_type, accepted, ip_address, user_agent)
                           VALUES ($1::uuid, $2, $3, $4, $5)""",
                        user_id, consent_type, accepted, ip, ua,
                    )

            # Mark onboarding complete
            await conn.execute(
                "UPDATE nf_users SET onboarding_completed = true, onboarding_completed_at = now() WHERE id = $1::uuid",
                user_id,
            )

        return {"recorded": True}
    except Exception:
        raise HTTPException(500, "Internal server error")


@router.get("/consent")
async def get_consent(request: Request):
    """Get user's consent status."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    data = verify_token(auth[7:])
    if not data:
        raise HTTPException(401, "Invalid token")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT consent_type, accepted, version, accepted_at
                   FROM user_consents WHERE user_id = $1::uuid AND revoked_at IS NULL
                   ORDER BY accepted_at DESC""",
                data["sub"],
            )
        return {
            "consents": [
                {"type": r["consent_type"], "accepted": r["accepted"], "version": r["version"], "at": r["accepted_at"].isoformat()}
                for r in rows
            ]
        }
    except Exception:
        return {"consents": []}
