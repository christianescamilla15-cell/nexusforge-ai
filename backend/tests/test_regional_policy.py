"""Tests for RegionalPolicy (P-014 / Gap O)."""
from __future__ import annotations

from pathlib import Path

from app.synth.profile import RegionalPolicy, load_profile


FIXTURE = (
    Path(__file__).parent.parent
    / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
)


def test_regional_policy_defaults():
    rp = RegionalPolicy()
    assert rp.region_scope == "country"
    assert rp.regions == []
    assert rp.externalization == "unknown"


def test_recommendation_for_hardcoded_flags_blocker():
    rp = RegionalPolicy(externalization="hardcoded", policy_type="refund-rules")
    rec = rp.refactor_recommendation()
    assert "hardcoded" in rec.lower()
    assert "expansion" in rec.lower() or "redeploy" in rec.lower()


def test_recommendation_for_config_file_suggests_rules_engine():
    rp = RegionalPolicy(externalization="config-file")
    rec = rp.refactor_recommendation()
    assert "rules engine" in rec.lower() or "rules-engine" in rec.lower()


def test_recommendation_for_rules_engine_is_terminal():
    rp = RegionalPolicy(externalization="rules-engine")
    rec = rp.refactor_recommendation()
    assert "target state" in rec.lower()


def test_recommendation_for_external_service_is_terminal():
    rp = RegionalPolicy(externalization="external-service")
    rec = rp.refactor_recommendation()
    assert "target state" in rec.lower() or "monitor" in rec.lower()


def test_recommendation_for_unknown_asks_for_data():
    rp = RegionalPolicy()
    rec = rp.refactor_recommendation()
    assert "determine" in rec.lower() or "unknown" in rec.lower()


def test_app_03_has_regional_policies_from_yaml():
    profile = load_profile(FIXTURE)
    app03 = next(a for a in profile.apps if a.codename == "app-03")
    assert len(app03.regional_policies) >= 1
    rp = app03.regional_policies[0]
    assert "BR" in rp.regions and "RU" in rp.regions
    assert rp.policy_type == "refund-rules"
    # Workshop Q B04 is still pending — externalization should be "unknown"
    assert rp.externalization == "unknown"


def test_other_apps_do_not_have_regional_policies():
    profile = load_profile(FIXTURE)
    for app in profile.apps:
        if app.codename == "app-03":
            continue
        assert app.regional_policies == [], (
            f"{app.codename} unexpectedly has regional_policies"
        )
