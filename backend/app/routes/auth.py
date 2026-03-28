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

DEMO_USERS = {
    'admin@nexusforge.ai': {'password': 'admin123', 'role': 'admin', 'id': 'user-001'},
    'member@nexusforge.ai': {'password': 'member123', 'role': 'member', 'id': 'user-002'},
    'viewer@nexusforge.ai': {'password': 'viewer123', 'role': 'viewer', 'id': 'user-003'},
}

@router.post('/auth/login', response_model=TokenResponse)
async def login(body: LoginRequest):
    user = DEMO_USERS.get(body.email)
    if not user or user['password'] != body.password:
        raise HTTPException(401, 'Invalid credentials')
    token = create_token(user['id'], body.email, user['role'])
    return TokenResponse(access_token=token, role=user['role'])

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
