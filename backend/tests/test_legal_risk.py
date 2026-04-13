"""Tests for LegalRisk (P-020 / Gap R)."""
from __future__ import annotations

from pathlib import Path

from app.synth.profile import LegalRisk, load_profile


FIXTURE = (
    Path(__file__).parent.parent
    / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
)


def test_legal_risk_defaults_are_non_blocking():
    lr = LegalRisk()
    assert lr.nda_status == "current"
    assert lr.nda_renewal_required is False
    assert lr.contract_coverage_pct == 100.0
    assert lr.blocks_sensitive_transfer() is False


def test_blocks_sensitive_transfer_for_possibly_expired():
    lr = LegalRisk(nda_status="possibly-expired", nda_renewal_required=True)
    assert lr.blocks_sensitive_transfer() is True


def test_blocks_sensitive_transfer_for_expired():
    lr = LegalRisk(nda_status="expired")
    assert lr.blocks_sensitive_transfer() is True


def test_blocks_sensitive_transfer_for_missing():
    lr = LegalRisk(nda_status="missing")
    assert lr.blocks_sensitive_transfer() is True


def test_current_nda_does_not_block():
    lr = LegalRisk(nda_status="current")
    assert lr.blocks_sensitive_transfer() is False


# ── YAML wiring ────────────────────────────────────────────────────────


def test_commercial_risk_has_legal_risk_block():
    profile = load_profile(FIXTURE)
    assert profile.commercial_risk is not None
    lr = profile.commercial_risk.legal_risk
    assert lr is not None
    assert lr.nda_signed_date == "2013-08-18"
    assert lr.nda_status == "possibly-expired"
    assert lr.nda_renewal_required is True
    assert lr.contract_coverage_pct == 60.0
    assert lr.uncovered_spend_usd == 3_400_000
    assert lr.paraguas_contract_signed_year == 2013
    assert lr.blocks_sensitive_transfer() is True


def test_legal_risk_roundtrip_via_to_dict():
    profile = load_profile(FIXTURE)
    d = profile.commercial_risk.to_dict()
    assert d["legal_risk"] is not None
    assert d["legal_risk"]["nda_status"] == "possibly-expired"
    assert d["legal_risk"]["uncovered_spend_usd"] == 3_400_000
