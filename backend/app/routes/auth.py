from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.auth.jwt_handler import create_token, verify_token
from app.auth.oauth import verify_google_token

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class OAuthRequest(BaseModel):
    provider: str = 'google'
    id_token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    role: str
    expires_in: int = 28800

@router.post('/auth/login', response_model=TokenResponse)
async def login(body: LoginRequest):
    """Login — delegates to main auth/routes.py. This is a fallback."""
    # Real login is handled by app.auth.routes — this route exists for backward compat
    from app.db.client import get_db_pool
    import bcrypt
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id, email, password_hash, role, is_active FROM nf_users WHERE email = $1",
                body.email,
            )
            if not user or not user["password_hash"]:
                raise HTTPException(401, "Invalid credentials")
            if not user["is_active"]:
                raise HTTPException(403, "Account disabled")
            if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
                raise HTTPException(401, "Invalid credentials")
            token = create_token(str(user["id"]), user["email"], user["role"] or "member")
            return TokenResponse(access_token=token, role=user["role"] or "member")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid credentials")

@router.post('/auth/oauth', response_model=TokenResponse)
async def oauth_login(body: OAuthRequest):
    google_user = await verify_google_token(body.id_token)
    if not google_user:
        raise HTTPException(401, 'Invalid OAuth token')
    token = create_token(google_user['sub'], google_user['email'], 'member')
    return TokenResponse(access_token=token, role='member')

@router.get('/auth/me')
async def get_current_user(request: Request):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        raise HTTPException(401, 'Not authenticated')
    data = verify_token(auth[7:])
    if not data:
        raise HTTPException(401, 'Invalid token')
    return {'user_id': data['sub'], 'email': data['email'], 'role': data['role']}
