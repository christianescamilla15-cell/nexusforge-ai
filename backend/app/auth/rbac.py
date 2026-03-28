"""Role-based access control middleware."""
from functools import wraps
from fastapi import Request, HTTPException
from app.auth.jwt_handler import verify_token

ROLES = {'admin': 4, 'owner': 3, 'member': 2, 'viewer': 1}

def require_role(minimum_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            auth = request.headers.get('Authorization', '') if request else ''
            if not auth.startswith('Bearer '):
                raise HTTPException(401, 'Missing or invalid token')
            token_data = verify_token(auth[7:])
            if not token_data:
                raise HTTPException(401, 'Invalid or expired token')
            user_role = token_data.get('role', 'viewer')
            if ROLES.get(user_role, 0) < ROLES.get(minimum_role, 0):
                raise HTTPException(403, f'Requires {minimum_role} role')
            request.state.user = token_data
            return await func(*args, request=request, **kwargs)
        return wrapper
    return decorator
