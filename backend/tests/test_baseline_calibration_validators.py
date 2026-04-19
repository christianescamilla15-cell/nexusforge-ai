"""Tests for the Pydantic Mythos baseline validator (Ruta B)."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.security.baseline_calibration import BaselineCalibration
from app.security.baseline_calibration_validators import (
    BaselineSchema,
    load_baseline_calibration_validated,
    validate_baseline_yaml,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "app" / "security" / "baselines" / "tenant-alpha-vulns-baseline.yaml"
)


@pytest.fixture(scope="module")
def raw_yaml() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


# ─── happy path ─────────────────────────────────────────────────────

def test_real_fixture_validates(raw_yaml):
    schema = validate_baseline_yaml(raw_yaml)
    assert isinstance(schema, BaselineSchema)
    assert schema.version == "1.0.0"
    assert len(schema.findings) >= 15
    assert set(schema.mitigations.keys()) == {"waf", "vault", "encrypted_config"}


def test_validated_matches_baseline_loader():
    v = load_baseline_calibration_validated()
    b = BaselineCalibration()
    assert v.is_loaded() and b.is_loaded()
    assert len(v.entries) == len(b.entries)
    assert list(v.mitigations) == list(b.mitigations)
    assert len(v.critical_entries()) == len(b.critical_entries())


# ─── strict-mode catches ────────────────────────────────────────────

def test_rejects_unknown_severity(raw_yaml):
    """`important` is a classic typo of severity — today it silently
    sorts as rank 2 in `_SEVERITY_ORDER.get(sev, 2)` and is impossible
    to distinguish from a real `medium` at scan time."""
    bad = copy.deepcopy(raw_yaml)
    bad["findings"][0]["severity"] = "important"
    with pytest.raises(ValidationError) as exc:
        validate_baseline_yaml(bad)
    assert "findings.0.severity" in str(exc.value)


def test_rejects_unknown_effective_severity(raw_yaml):
    bad = copy.deepcopy(raw_yaml)
    bad["findings"][0]["effective_severity"] = "medium-high"
    with pytest.raises(ValidationError) as exc:
        validate_baseline_yaml(bad)
    assert "effective_severity" in str(exc.value)


def test_rejects_finding_missing_id(raw_yaml):
    bad = copy.deepcopy(raw_yaml)
    del bad["findings"][0]["id"]
    with pytest.raises(ValidationError) as exc:
        validate_baseline_yaml(bad)
    assert "findings.0.id" in str(exc.value)


def test_rejects_finding_missing_category(raw_yaml):
    bad = copy.deepcopy(raw_yaml)
    del bad["findings"][0]["category"]
    with pytest.raises(ValidationError) as exc:
        validate_baseline_yaml(bad)
    assert "findings.0.category" in str(exc.value)


def test_rejects_wrong_mitigation_shape(raw_yaml):
    """If someone replaces a mitigation dict with a bare string, Mythos
    today silently drops its `applies_to` / `blocks_patterns`; Pydantic
    refuses to coerce."""
    bad = copy.deepcopy(raw_yaml)
    bad["mitigations"]["waf"] = "corporate-cliente"
    with pytest.raises(ValidationError):
        validate_baseline_yaml(bad)


def test_rejects_non_bool_on_premise(raw_yaml):
    bad = copy.deepcopy(raw_yaml)
    bad["mitigations"]["vault"]["on_premise"] = "yes please"
    with pytest.raises(ValidationError):
        validate_baseline_yaml(bad)


# ─── tolerance ──────────────────────────────────────────────────────

def test_tolerates_extra_finding_fields(raw_yaml):
    """The real fixture uses `notes`, `affected_modules`, `conflict_note`,
    `metric` — all outside the dataclass today. Validator must not
    block them (extra='ignore')."""
    schema = validate_baseline_yaml(raw_yaml)
    # If we got here, the extras were tolerated. Sanity check: entries
    # that had extras survive into the validated list.
    ids = {f.id for f in schema.findings}
    assert "bsp-upload-no-validation" in ids       # had `note`
    assert "comisiones-parameterscontext-god-class" in ids  # had `affected_modules`


def test_missing_baseline_file_returns_unloaded(tmp_path):
    nonexistent = tmp_path / "missing.yaml"
    calib = load_baseline_calibration_validated(nonexistent)
    assert calib.is_loaded() is False
    assert calib.entries == []
