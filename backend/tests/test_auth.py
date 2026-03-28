"""Tests for JWT authentication, RBAC, and Google OAuth."""
import time
import pytest
import jwt
from unittest.mock import patch

from app.auth.jwt_handler import create_token, verify_token, get_role, SECRET, ALGORITHM
from app.auth.rbac import ROLES


# --- JWT handler tests ---

def test_create_token_returns_string():
    token = create_token('user-001', 'test@nexusforge.ai', 'admin')
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_valid_token():
    token = create_token('user-001', 'test@nexusforge.ai', 'member')
    data = verify_token(token)
    assert data is not None
    assert data['sub'] == 'user-001'
    assert data['email'] == 'test@nexusforge.ai'
    assert data['role'] == 'member'


def test_verify_expired_token():
    payload = {
        'sub': 'user-001', 'email': 'test@nexusforge.ai', 'role': 'member',
        'iat': int(time.time()) - 7200, 'exp': int(time.time()) - 3600,
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    assert verify_token(token) is None


def test_verify_invalid_token():
    assert verify_token('totally.invalid.token') is None
    assert verify_token('') is None


def test_role_hierarchy():
    assert ROLES['admin'] > ROLES['owner']
    assert ROLES['owner'] > ROLES['member']
    assert ROLES['member'] > ROLES['viewer']


# --- Route tests (using FastAPI TestClient) ---

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.routes.auth import router
    from fastapi import FastAPI
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


def test_login_success(client):
    resp = client.post('/auth/login', json={'email': 'admin@nexusforge.ai', 'password': 'admin123'})
    assert resp.status_code == 200
    body = resp.json()
    assert 'access_token' in body
    assert body['role'] == 'admin'
    assert body['token_type'] == 'bearer'


def test_login_invalid_credentials(client):
    resp = client.post('/auth/login', json={'email': 'admin@nexusforge.ai', 'password': 'wrong'})
    assert resp.status_code == 401


def test_oauth_demo_mode(client):
    resp = client.post('/auth/oauth', json={'provider': 'google', 'id_token': 'demo'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['role'] == 'member'
    assert 'access_token' in body


def test_get_me_with_token(client):
    # First login to get a token
    login_resp = client.post('/auth/login', json={'email': 'member@nexusforge.ai', 'password': 'member123'})
    token = login_resp.json()['access_token']
    # Use it on /auth/me
    resp = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['email'] == 'member@nexusforge.ai'
    assert body['role'] == 'member'


def test_get_me_without_token(client):
    resp = client.get('/auth/me')
    assert resp.status_code == 401
