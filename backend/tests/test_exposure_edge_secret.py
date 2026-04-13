"""Tests for P-009 (ExposureProfile) + P-011 (EdgeSecurity) + P-010 (SecretManagement).

Covers:
- Dataclass defaults are safe for opt-out.
- YAML parsing from tenant_alpha.yaml populates each block.
- app-03 exposure: public-internet + dual_backend + WAF + geo RU/KP.
- app-01 exposure: private-vpn + 2FA + WAF at site layer.
- InfrastructureRisk.edge_security present with WAF details.
- SecretManagement present with "Bolt" alias.
- Opt-out apps (not declaring exposure) return None.
"""
from __future__ import annotations

from pathlib import Path

from app.synth.profile import (
    AppRecipe,
    EdgeSecurity,
    ExposureProfile,
    SecretManagement,
    load_profile,
)


FIXTURE = (
    Path(__file__).parent.parent
    / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
)


# ── Dataclass defaults ────────────────────────────────────────────────


def test_exposure_defaults_are_safe():
    ep = ExposureProfile()
    assert ep.surface == "internal-only"
    assert ep.dual_backend is False
    assert ep.auth_layers == []
    assert ep.edge_protection == "none"
    assert ep.user_count == 0
    assert ep.mfa_required is False


def test_edge_security_defaults_are_safe():
    es = EdgeSecurity()
    assert es.waf_present is False
    assert es.waf_provider == "none"
    assert es.geo_blocking == []
    assert es.pattern_rules == []


def test_secret_management_defaults_are_safe():
    sm = SecretManagement()
    assert sm.product == "env-vars"
    assert sm.internal_alias == ""
    assert sm.hash_based_injection is False
    assert sm.on_premise is False


def test_app_recipe_exposure_defaults_none():
    r = AppRecipe(
        codename="foo", label="Foo",
        loc_target=10_000, primary_language="python",
    )
    assert r.exposure is None
    assert r.multi_robot is None


# ── YAML parsing — tenant_alpha fixture ───────────────────────────────


def test_app_01_exposure_is_private_vpn():
    profile = load_profile(FIXTURE)
    app = next(a for a in profile.apps if a.codename == "app-01")
    assert app.exposure is not None
    assert app.exposure.surface == "private-vpn"
    assert "vpn" in app.exposure.auth_layers
    assert "2fa" in app.exposure.auth_layers
    assert app.exposure.edge_protection == "waf"
    assert app.exposure.mfa_required is True
    assert app.exposure.user_count == 6


def test_app_02_exposure_is_internal_only():
    profile = load_profile(FIXTURE)
    app = next(a for a in profile.apps if a.codename == "app-02")
    assert app.exposure is not None
    assert app.exposure.surface == "internal-only"
    assert app.exposure.dual_backend is False


def test_app_03_exposure_is_public_internet_with_dual_backend():
    """The ARC sub-project is public Internet with public + VPN back-ends."""
    profile = load_profile(FIXTURE)
    app = next(a for a in profile.apps if a.codename == "app-03")
    assert app.exposure is not None
    assert app.exposure.surface == "public-internet"
    assert app.exposure.dual_backend is True
    assert app.exposure.edge_protection == "waf"
    # Geo-blocking must reflect H-119 (Rusia + Corea del Sur)
    assert "RU" in app.exposure.geo_restrictions
    assert "KP" in app.exposure.geo_restrictions


def test_app_04_and_05_exposures_are_internal():
    profile = load_profile(FIXTURE)
    app04 = next(a for a in profile.apps if a.codename == "app-04")
    app05 = next(a for a in profile.apps if a.codename == "app-05")
    assert app04.exposure is not None and app04.exposure.surface == "internal-only"
    assert app05.exposure is not None and app05.exposure.surface == "internal-only"


# ── EdgeSecurity on InfrastructureRisk ────────────────────────────────


def test_infrastructure_risk_has_edge_security_block():
    profile = load_profile(FIXTURE)
    assert profile.infrastructure_risk is not None
    es = profile.infrastructure_risk.edge_security
    assert es is not None
    assert es.waf_present is True
    assert es.waf_provider == "corporate"
    assert "RU" in es.geo_blocking and "KP" in es.geo_blocking
    assert "sqli" in es.pattern_rules
    assert "xss" in es.pattern_rules
    assert es.scan_cadence == "continuous"


# ── SecretManagement at tenant level ──────────────────────────────────


def test_secret_management_is_hashicorp_vault_with_bolt_alias():
    """H-118 — platform-vendor's Vault uses the internal alias 'Bolt'."""
    profile = load_profile(FIXTURE)
    sm = profile.secret_management
    assert sm is not None
    assert sm.product == "hashicorp-vault"
    assert sm.internal_alias == "Bolt"
    assert sm.scope == "per-app"
    assert sm.hash_based_injection is True
    assert sm.on_premise is True
    assert sm.rotates_users is True
    # Workshop W2: DB creds NOT rotated
    assert sm.rotates_db_creds is False
