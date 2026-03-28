"""JWT token creation and verification with role-based claims."""
import jwt
import time
from app.config import settings

SECRET = settings.jwt_secret if hasattr(settings, 'jwt_secret') else 'nexusforge-dev-secret-2026'
ALGORITHM = 'HS256'
TOKEN_EXPIRY = 3600 * 8  # 8 hours

def create_token(user_id: str, email: str, role: str = 'member') -> str:
    payload = {
        'sub': user_id, 'email': email, 'role': role,
        'iat': int(time.time()), 'exp': int(time.time()) + TOKEN_EXPIRY,
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def get_role(token_data: dict) -> str:
    return token_data.get('role', 'viewer')
