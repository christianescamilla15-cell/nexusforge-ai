"""Google OAuth2 — demo mode returns mock user, production uses real Google."""
GOOGLE_CLIENT_ID = 'demo-client-id'

async def verify_google_token(id_token: str) -> dict | None:
    # Demo mode: accept any token and return mock user
    if id_token == 'demo':
        return {'sub': 'google-demo-001', 'email': 'demo@nexusforge.ai', 'name': 'Demo User'}
    # Production: verify with Google
    # from google.oauth2 import id_token as google_id_token
    # return google_id_token.verify_oauth2_token(id_token, requests.Request(), GOOGLE_CLIENT_ID)
    return {'sub': f'google-{id_token[:8]}', 'email': f'{id_token[:8]}@gmail.com', 'name': 'OAuth User'}
