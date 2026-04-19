"""Tests for the Pydantic ecosystem-health validator (Ruta B)."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.synth.ecosystem_metrics import load_ecosystem_metrics
from app.synth.ecosystem_metrics_validators import (
    EcosystemHealthSchema,
    load_ecosystem_metrics_validated,
    validate_ecosystem_yaml,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "app" / "synth" / "fixtures" / "tenant-alpha-ecosystem-health.yaml"
)


@pytest.fixture(scope="module")
def raw_yaml() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


# ─── happy path ─────────────────────────────────────────────────────

def test_real_fixture_validates(raw_yaml):
    schema = validate_ecosystem_yaml(raw_yaml)
    assert isinstance(schema, EcosystemHealthSchema)
    assert schema.tenant_id == "tenant-alpha"
    assert schema.ecosystem is not None
    assert schema.ecosystem.total_issues == 189_997
    assert len(schema.per_app_critical) >= 5


def test_validated_matches_baseline_loader():
    v = load_ecosystem_metrics_validated()
    b = load_ecosystem_metrics()
    assert v == b
    assert v.is_loaded()
    assert v.total_issues == 189_997
    assert v.risk_total_usd == 18_500_000


# ─── strict-mode catches ────────────────────────────────────────────

def test_rejects_unknown_nda_status(raw_yaml):
    bad = copy.deepcopy(raw_yaml)
    bad["legal"]["nda"]["status"] = "expiring-soon"
    with pytest.raises(ValidationError) as exc:
        validate_ecosystem_yaml(bad)
    assert "legal.nda.status" in str(exc.value)


def test_rejects_non_numeric_issue_count(raw_yaml):
    bad = copy.deepcopy(raw_yaml)
    bad["ecosystem"]["total_issues"] = "one-hundred-eighty-nine-thousand"
    with pytest.raises(ValidationError) as exc:
        validate_ecosystem_yaml(bad)
    assert "total_issues" in str(exc.value)


def test_rejects_missing_required_app_field_in_per_app_critical(raw_yaml):
    """Each row in per_app_critical needs an `app` codename."""
    bad = copy.deepcopy(raw_yaml)
    del bad["per_app_critical"][0]["app"]
    with pytest.raises(ValidationError) as exc:
        validate_ecosystem_yaml(bad)
    assert "per_app_critical.0.app" in str(exc.value)


def test_rejects_wrong_structural_type(raw_yaml):
    """A string where a dict is expected is rejected with a precise path."""
    bad = copy.deepcopy(raw_yaml)
    bad["commercial"] = "just a label"
    with pytest.raises(ValidationError):
        validate_ecosystem_yaml(bad)


# ─── tolerance ──────────────────────────────────────────────────────

def test_extra_unknown_keys_are_ignored(raw_yaml):
    tolerant = copy.deepcopy(raw_yaml)
    tolerant["future_section"] = {"x": 1}
    tolerant["ecosystem"]["future_metric"] = 42
    schema = validate_ecosystem_yaml(tolerant)
    assert schema.ecosystem.total_issues == 189_997


def test_missing_fixture_still_returns_empty_metrics(tmp_path):
    """Graceful fallback for non-existent path preserves existing behavior."""
    nonexistent = tmp_path / "does-not-exist.yaml"
    metrics = load_ecosystem_metrics_validated(nonexistent)
    assert metrics.is_loaded() is False
    assert metrics.total_issues == 0


def test_empty_yaml_validates_as_empty_schema(tmp_path):
    """An empty YAML (just a comment) doesn't blow up — matches the
    tolerant-by-default posture of the existing loader."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("# empty\n", encoding="utf-8")
    metrics = load_ecosystem_metrics_validated(empty)
    # Empty YAML → empty dict after safe_load → empty schema → empty metrics.
    # `_loaded` remains False because the loader only flips it when
    # content is actually present.
    assert metrics.total_issues == 0
