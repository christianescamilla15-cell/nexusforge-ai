"""Pydantic validator for the Mythos baseline YAML boundary (Ruta B).

Parallel to `baseline_calibration.py` — validates the raw YAML dict
shape before `BaselineCalibration` constructs dataclasses from it.
`baseline_calibration.py` is not modified.

Opt-in usage:
    >>> from app.security.baseline_calibration_validators import (
    ...     load_baseline_calibration_validated,
    ... )
    >>> calib = load_baseline_calibration_validated()

If the YAML fails validation, `pydantic.ValidationError` is raised with
a precise path. Unlike `BaselineCalibration.__init__` (never raises on
parse failure), this entry point raises on structural errors — which is
the point: Mythos calibration silently dropping entries because of a
typo in `severity` or a wrong category is exactly the kind of bug we
want to surface at load time.

Design notes:
    - Severity is a Literal (one of the 5 rank keys used in
      `_SEVERITY_ORDER`). Any other value silently sorts as rank 2
      today and disappears into the middle of the pile.
    - Category is NOT enumerated: the 9 Mythos scan categories live in
      the scanner layer and we don't want to double-source their list.
      Category is validated as non-empty string instead.
    - Fields outside the dataclass (`notes`, `affected_modules`,
      `conflict_note`, `metric`) are accepted via `extra='ignore'` so
      the validator does not block YAML rows that exist today.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.security.baseline_calibration import BaselineCalibration


_CONFIG = ConfigDict(strict=False, extra="ignore", frozen=False)


class _Base(BaseModel):
    model_config = _CONFIG


SeverityLiteral = Literal["critical", "high", "medium", "low", "info"]


class MitigationSchema(_Base):
    # Note: the mitigation NAME is the YAML dict key (waf / vault /
    # encrypted_config). That key becomes the `name` field in the
    # `Mitigation` dataclass but is not present inside the value dict.
    provider: str = ""
    applies_to: list[str] = Field(default_factory=list)
    blocks_patterns: list[str] = Field(default_factory=list)
    effect: str = ""
    internal_alias: str = ""
    on_premise: bool = False


class FindingEntrySchema(_Base):
    id: str
    app: str = ""
    category: str                          # see module docstring on why not Literal
    pattern_match: list[str] = Field(default_factory=list)
    cwe: str = ""
    severity: SeverityLiteral = "medium"
    # Mythos rank uses these as the final severity after mitigations.
    # Empty string = no downgrade (keep severity). Represented as string
    # to preserve "" sentinel from the YAML instead of forcing a union.
    effective_severity: SeverityLiteral | Literal[""] = ""
    remediation_status: str = ""
    remediation_phase: str = ""
    remediation_target: str = ""
    mitigation_layer: str = ""
    quick_win: str = ""
    priority: str = ""
    context: str = ""
    note: str = ""
    source: str = ""


class EcosystemContextSchema(_Base):
    total_loc: int = 0
    total_issues: int = 0
    critical_issues: int = 0
    critical_density_pct: float = 0.0
    apps_without_tests: int = 0
    apps_without_cicd: int = 0
    sql_concat_count: int = 0
    tables_without_fk_pct: float = 0.0


class RiskExposureUsdSchema(_Base):
    reputational: float = 0.0
    pii: float = 0.0
    integrity: float = 0.0
    total: float = 0.0


class BaselineSchema(_Base):
    version: str = "unknown"
    generated: str = ""
    mitigations: dict[str, MitigationSchema] = Field(default_factory=dict)
    findings: list[FindingEntrySchema] = Field(default_factory=list)
    ecosystem_context: EcosystemContextSchema | None = None
    risk_exposure_usd: RiskExposureUsdSchema | None = None


# ─── public entry points ────────────────────────────────────────────

def validate_baseline_yaml(raw: dict[str, Any]) -> BaselineSchema:
    """Validate a raw Mythos baseline YAML dict."""
    return BaselineSchema.model_validate(raw or {})


def load_baseline_calibration_validated(
    path: str | Path | None = None,
) -> BaselineCalibration:
    """Validate the baseline YAML then construct `BaselineCalibration`.

    Missing file → passthrough to the original constructor (which
    tolerates absent fixtures by returning an unloaded instance).
    Present-but-malformed file → `pydantic.ValidationError` with a
    precise path, raised before Mythos can silently drop entries.
    """
    target = (
        Path(path)
        if path is not None
        else Path(__file__).parent / "baselines" / "tenant-alpha-vulns-baseline.yaml"
    )
    if not target.is_file():
        return BaselineCalibration(target)
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    validate_baseline_yaml(raw)
    return BaselineCalibration(target)
