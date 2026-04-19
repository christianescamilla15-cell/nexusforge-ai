"""Pydantic validator for the ecosystem-health YAML boundary (Ruta B).

Parallel to `ecosystem_metrics.py` (dataclasses + graceful loader) — this
module validates the raw YAML dict shape before the existing loader
constructs dataclasses. `ecosystem_metrics.py` is not modified.

Opt-in usage:
    >>> from app.synth.ecosystem_metrics_validators import load_ecosystem_metrics_validated
    >>> metrics = load_ecosystem_metrics_validated()

If the YAML fails validation, `pydantic.ValidationError` is raised with
a precise path. This is a *stricter* contract than the existing
`load_ecosystem_metrics` (which never raises and returns empty metrics
on parse failure). Callers that need the tolerant behavior keep the old
loader; callers that want type safety opt in.

Type policy matches `profile_validators.py`: non-strict coercion (YAML
int → Python float for monetary fields), `extra='ignore'` for tolerance.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.synth.ecosystem_metrics import EcosystemMetrics, load_ecosystem_metrics


_STRICT_CONFIG = ConfigDict(strict=False, extra="ignore", frozen=False)


class _Base(BaseModel):
    model_config = _STRICT_CONFIG


# ─── ecosystem totals ───────────────────────────────────────────────

class EcosystemTotalsSchema(_Base):
    total_loc: int = 0
    total_apps: int = 0
    total_components: int = 0
    total_issues: int = 0
    satellite_issues: int = 0
    core_cobol_issues: int = 0
    critical_issues: int = 0
    critical_density_pct: float = 0.0
    apps_without_tests: int = 0
    apps_without_tests_total: int = 0
    apps_without_cicd: int = 0
    apps_without_cicd_total: int = 0
    sql_concat_queries: int = 0
    tables_without_fk_pct: float = 0.0
    pii_items: int = 0
    pii_inputs: int = 0
    db_growth_monthly_pct: float = 0.0


class RiskExposureSchema(_Base):
    reputational: float = 0.0
    pii: float = 0.0
    integrity: float = 0.0
    total: float = 0.0
    basis: str = ""


class ParaguasContractSchema(_Base):
    name: str = ""
    signed_year: int = 0
    age_years: int = 0


class CommercialSchema(_Base):
    platform_vendor_facturacion_usd: float = 0.0
    contract_coverage_pct: float = 100.0
    uncovered_spend_usd: float = 0.0
    invoices_total: int = 0
    contracts_total: int = 0
    paraguas_contract: ParaguasContractSchema | None = None
    bpo_size_min: int = 0
    bpo_size_max: int = 0
    client_revenue_share_of_vendor_pct: float = 0.0


class NdaSchema(_Base):
    signed_date: str = ""
    status: Literal["current", "possibly-expired", "expired", "missing"] = "current"
    renewal_required_before_transfer: bool = False
    notes: str = ""


class LegalSchema(_Base):
    nda: NdaSchema | None = None


# ─── per-app + systemic + priority rows ─────────────────────────────

class PerAppCriticalRowSchema(_Base):
    app: str
    label: str = ""
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    blocker_issues: int = 0
    critical_density_pct: float = 0.0
    # free text — real hostings include "aws", "on-premise",
    # "aws-platform-vendor", "conflict-pending", "hybrid-aws-as400",
    # "on-premise-estimated". Don't enum this today; fixture-driven.
    hosting: str = ""
    notes: str = ""


class SystemicPatternRowSchema(_Base):
    pattern: str
    prevalence: str = ""
    prevalence_pct: float | None = None
    count: int | None = None
    note: str = ""


class PriorityHintRowSchema(_Base):
    app: str
    priority_score: float = 0.0
    rationale: str = ""


# ─── top-level schema ───────────────────────────────────────────────

class EcosystemHealthSchema(_Base):
    version: str = ""
    generated: str = ""
    tenant_id: str = ""
    ecosystem: EcosystemTotalsSchema | None = None
    risk_exposure_usd: RiskExposureSchema | None = None
    commercial: CommercialSchema | None = None
    legal: LegalSchema | None = None
    per_app_critical: list[PerAppCriticalRowSchema] = Field(default_factory=list)
    systemic_patterns: list[SystemicPatternRowSchema] = Field(default_factory=list)
    priority_hints: list[PriorityHintRowSchema] = Field(default_factory=list)


# ─── public entry points ────────────────────────────────────────────

def validate_ecosystem_yaml(raw: dict[str, Any]) -> EcosystemHealthSchema:
    """Validate a raw ecosystem-health YAML dict.

    Raises `pydantic.ValidationError` with a precise path on malformed
    input. Unknown top-level keys are ignored (matches the tolerant
    loader convention).
    """
    return EcosystemHealthSchema.model_validate(raw or {})


def load_ecosystem_metrics_validated(
    path: str | Path | None = None,
) -> EcosystemMetrics:
    """Parse YAML, validate with Pydantic, then delegate to the existing
    `load_ecosystem_metrics`.

    Unlike `load_ecosystem_metrics` (which never raises and returns
    empty metrics on parse failure), this entry point **raises
    ValidationError** when the YAML is structurally wrong. Missing
    fixture is still tolerated (returns empty metrics, like the
    original) — validation only runs if a file exists.
    """
    target = (
        Path(path)
        if path is not None
        else Path(__file__).parent / "fixtures" / "tenant-alpha-ecosystem-health.yaml"
    )
    if not target.is_file():
        return load_ecosystem_metrics(target)  # graceful empty
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    validate_ecosystem_yaml(raw)
    return load_ecosystem_metrics(target)
