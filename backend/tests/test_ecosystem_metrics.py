"""Tests for ecosystem metrics loader (P-021)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.synth.ecosystem_metrics import (
    EcosystemMetrics,
    load_ecosystem_metrics,
    _YAML_AVAILABLE,
)


FIXTURE_PATH = (
    Path(__file__).parent.parent
    / "app"
    / "synth"
    / "fixtures"
    / "tenant-alpha-ecosystem-health.yaml"
)


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_default_fixture_loads():
    m = load_ecosystem_metrics()
    assert m.is_loaded() is True
    assert m.version == "1.0.0"
    assert m.tenant_id == "tenant-alpha"


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_ecosystem_totals_match_entregables():
    """Totals must match the canonical numbers from Report Out + SonarQube."""
    m = load_ecosystem_metrics()
    assert m.total_loc == 5_634_738
    assert m.total_apps == 31
    assert m.total_issues == 189_997
    assert m.satellite_issues == 166_714
    assert m.core_cobol_issues == 23_283
    assert m.critical_issues == 13_547
    assert m.critical_density_pct == pytest.approx(8.1)
    assert m.apps_without_tests == 12
    assert m.apps_without_cicd == 11


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_risk_exposure_totals_18_5m():
    m = load_ecosystem_metrics()
    assert m.risk_reputational_usd == 13_000_000
    assert m.risk_pii_usd == 5_000_000
    assert m.risk_integrity_usd == 500_000
    assert m.risk_total_usd == 18_500_000
    assert "Armor" in m.risk_basis


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_commercial_signals():
    m = load_ecosystem_metrics()
    assert m.commercial.facturacion_usd == 8_662_761
    assert m.commercial.contract_coverage_pct == pytest.approx(60.0)
    assert m.commercial.uncovered_spend_usd == 3_400_000
    assert m.commercial.invoices_total == 286
    assert m.commercial.contracts_total == 23
    assert m.commercial.paraguas_contract_signed_year == 2013
    assert "2013" in m.commercial.paraguas_contract_name


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_legal_nda_flagged_as_possibly_expired():
    m = load_ecosystem_metrics()
    assert m.legal.nda_signed_date == "2013-08-18"
    assert m.legal.nda_status == "possibly-expired"
    assert m.legal.renewal_required_before_transfer is True
    assert len(m.legal.nda_notes) > 0


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_per_app_density_includes_all_scope_apps():
    m = load_ecosystem_metrics()
    codenames = {a.app for a in m.per_app}
    for expected in ["app-01", "app-02", "app-03-arc", "app-03-bsp", "app-04", "app-05"]:
        assert expected in codenames, f"missing {expected}"


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_app_03_arc_is_most_critical_density():
    m = load_ecosystem_metrics()
    arc = m.app("app-03-arc")
    assert arc is not None
    assert arc.critical_issues == 9
    # 92% of ARC findings are security — density > 50%
    assert arc.critical_density_pct > 50.0


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_app_03_bsp_has_blockers_and_conflict_hosting():
    m = load_ecosystem_metrics()
    bsp = m.app("app-03-bsp")
    assert bsp is not None
    assert bsp.blocker_issues == 6
    assert bsp.total_issues == 195
    assert "conflict" in bsp.hosting or bsp.hosting == "conflict-pending"


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_priority_hints_ranked_correctly():
    m = load_ecosystem_metrics()
    ranked = m.ranked_by_priority()
    assert ranked[0].app == "app-03-arc"  # highest priority_score 50.8
    assert ranked[-1].app == "app-04"     # lowest (10.0) — pending workshop


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_systemic_patterns_cover_key_findings():
    m = load_ecosystem_metrics()
    patterns = {p.pattern for p in m.systemic_patterns}
    assert "credentials-in-config" in patterns
    assert "zero-automated-tests" in patterns
    assert "sql-concatenation-sqli-risk" in patterns
    assert "tables-without-fk" in patterns


def test_missing_fixture_returns_empty_metrics(tmp_path):
    """Missing path returns empty metrics without raising."""
    m = load_ecosystem_metrics(tmp_path / "does-not-exist.yaml")
    assert m.is_loaded() is False
    assert m.total_issues == 0
    assert m.risk_total_usd == 0.0


@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
def test_summary_contains_key_fields():
    m = load_ecosystem_metrics()
    s = m.summary()
    assert s["loaded"] is True
    assert s["total_issues"] == 189_997
    assert s["risk_total_usd"] == 18_500_000
    assert s["per_app_count"] >= 5
