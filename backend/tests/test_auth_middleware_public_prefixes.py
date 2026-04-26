"""Tests for the H-4 PUBLIC_PREFIXES exact-segment boundary fix.

The prior implementation used `path.startswith(p)`, which let any
future route like `/api/refactor/showcase-debug` slip through auth
because it started with `/api/refactor/showcase`. The new
`_is_public(path)` requires the path to either equal a prefix exactly
or be a proper path-segment child (`prefix + "/" + ...`).
"""
from __future__ import annotations

import pytest

from app.auth.middleware import _is_public


# ─── exact-match public paths ─────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/api/health",
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/google",
    "/api/auth/plans",
    "/api/integrations/status",
])
def test_exact_public_paths_are_exempt(path):
    assert _is_public(path) is True


# ─── prefix child paths (proper subpaths) ────────────────────────────

@pytest.mark.parametrize("path", [
    "/api/auth/refresh",
    "/api/auth/forgot-password",
    "/api/templates",
    "/api/templates/wizard-recipe-1",
    "/api/automations/webhook/abc123",
    "/api/mythos",
    "/api/mythos/scan",
    "/api/mythos/scan/secrets",
    "/api/refactor/showcase",
    "/api/refactor/showcase/tenant-alpha",
    "/api/v1/refactor/showcase/tenant-alpha",
])
def test_legitimate_subpaths_are_exempt(path):
    assert _is_public(path) is True


# ─── H-4 regression: substring collisions are NOT exempt ─────────────

@pytest.mark.parametrize("path", [
    "/api/mythos-internal",            # not /api/mythos/...
    "/api/mythos-debug",
    "/api/refactor/showcase-debug",    # not /api/refactor/showcase/...
    "/api/refactor/showcase-internal",
    "/api/templates-private",          # not /api/templates/...
    "/api/templates-admin",
    "/api/auth-bypass",                # not /api/auth/...
    "/api/v1/refactor/showcase-debug",
])
def test_substring_collisions_require_auth(path):
    """H-4 regression: a sibling path that *starts with* a public
    prefix string but is not a child of that namespace must require
    auth. This is the exact attack vector the retro called out."""
    assert _is_public(path) is False, (
        f"H-4 regression: {path!r} should require auth (sibling to a public prefix)"
    )


# ─── unrelated paths are not public ──────────────────────────────────

@pytest.mark.parametrize("path", [
    "/api/workflows",
    "/api/workflows/abc-123",
    "/api/agents",
    "/api/billing/checkout",
    "/api/refactor/ingest",
    "/api/executions-db",
    "/admin",
    "/",
])
def test_protected_paths_require_auth(path):
    assert _is_public(path) is False
