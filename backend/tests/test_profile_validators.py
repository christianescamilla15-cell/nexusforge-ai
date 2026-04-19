"""Tests for the Pydantic tenant-profile validator (Ruta B).

Covers:
- happy path: real fixture validates AND produces a dataclass identical
  to `load_profile` (byte-for-byte equality)
- strict-mode catches: unknown Literal values, wrong structural types,
  missing required fields
- tolerance: unknown top-level keys are ignored (matches `load_profile`)

`profile.py` is untouched — the validator is a parallel opt-in entry
point. `pydantic.ValidationError` is raised at the boundary with a
precise path so callers see *where* the YAML is wrong.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.synth.profile import load_profile
from app.synth.profile_validators import (
    TenantProfileSchema,
    load_profile_validated,
    validate_tenant_yaml,
)


FIXTURE = Path(__file__).resolve().parents[1] / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"


@pytest.fixture(scope="module")
def raw_yaml() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


# ─── happy path ─────────────────────────────────────────────────────

def test_real_fixture_validates(raw_yaml):
    schema = validate_tenant_yaml(raw_yaml)
    assert isinstance(schema, TenantProfileSchema)
    assert schema.tenant_id == "tenant-alpha"
    assert len(schema.apps) >= 5


def test_validated_profile_equals_baseline_dataclass():
    """Contract: `load_profile_validated` is observationally identical
    to `load_profile` for a valid fixture — zero behavior change for
    consumers that opt in."""
    validated = load_profile_validated(FIXTURE)
    baseline = load_profile(FIXTURE)
    assert validated == baseline
    assert validated.total_apps() == baseline.total_apps()
    assert validated.total_loc() == baseline.total_loc()
    assert validated.total_vulnerabilities() == baseline.total_vulnerabilities()


# ─── strict-mode catches ────────────────────────────────────────────

def test_rejects_unknown_orchestrator_value(raw_yaml):
    """Typo in a Literal is caught with a clear path."""
    bad = copy.deepcopy(raw_yaml)
    bad.setdefault("infrastructure_risk", {})["orchestrator"] = "airfow"
    with pytest.raises(ValidationError) as exc:
        validate_tenant_yaml(bad)
    err = str(exc.value)
    assert "infrastructure_risk.orchestrator" in err
    assert "airfow" in err


def test_rejects_unknown_certification_status(raw_yaml):
    """`complet` (typo of `complete`) is rejected."""
    bad = copy.deepcopy(raw_yaml)
    bad["compliance"]["certifications"][0]["status"] = "complet"
    with pytest.raises(ValidationError) as exc:
        validate_tenant_yaml(bad)
    assert "compliance.certifications.0.status" in str(exc.value)


def test_rejects_unknown_database_engine(raw_yaml):
    """Engine typo is rejected before it becomes a silent runtime bug."""
    bad = copy.deepcopy(raw_yaml)
    bad["apps"][0]["databases"][0]["engine"] = "postgres-wrong"
    with pytest.raises(ValidationError) as exc:
        validate_tenant_yaml(bad)
    assert "engine" in str(exc.value)


def test_rejects_structurally_wrong_type(raw_yaml):
    """A list where a string is expected is rejected."""
    bad = copy.deepcopy(raw_yaml)
    bad["tenant_id"] = ["wrong", "shape"]
    with pytest.raises(ValidationError):
        validate_tenant_yaml(bad)


def test_rejects_missing_required_top_level_field(raw_yaml):
    """Missing `tenant_id` or `display_name` fails loudly."""
    bad = copy.deepcopy(raw_yaml)
    del bad["tenant_id"]
    with pytest.raises(ValidationError) as exc:
        validate_tenant_yaml(bad)
    assert "tenant_id" in str(exc.value)


def test_rejects_missing_app_codename(raw_yaml):
    """A required field inside a nested list is still caught with a
    precise path."""
    bad = copy.deepcopy(raw_yaml)
    del bad["apps"][0]["codename"]
    with pytest.raises(ValidationError) as exc:
        validate_tenant_yaml(bad)
    assert "apps.0.codename" in str(exc.value)


# ─── tolerance ──────────────────────────────────────────────────────

def test_extra_unknown_keys_are_ignored(raw_yaml):
    """Matches `load_profile`'s `.get(..., default)` tolerance — unknown
    keys are dropped silently (can be tightened to `extra='forbid'`
    later after a fixture audit)."""
    tolerant = copy.deepcopy(raw_yaml)
    tolerant["some_new_future_field"] = {"not": "yet", "known": True}
    tolerant["apps"][0]["experimental_knob"] = 42
    schema = validate_tenant_yaml(tolerant)
    assert schema.tenant_id == "tenant-alpha"


def test_non_scope_apps_accept_short_form_string(raw_yaml):
    """The existing loader supports `non_scope_apps: ['app-06', ...]`
    as a shortcut for dict-form entries; the validator does too."""
    variant = copy.deepcopy(raw_yaml)
    variant.setdefault("non_scope_apps", []).append("app-99")
    schema = validate_tenant_yaml(variant)
    assert "app-99" in [
        entry if isinstance(entry, str) else entry.codename
        for entry in schema.non_scope_apps
    ]
