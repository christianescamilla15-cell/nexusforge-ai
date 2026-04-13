"""Ecosystem metrics loader (P-021).

Loads the ``tenant-alpha-ecosystem-health.yaml`` fixture and exposes
quantitative signals consumed by:

- Report Out simulator (realistic scale numbers)
- strangler_planner (priority ordering when combined with DiscoveryIndex)
- Internal tests (validation that NexusForge behavior matches the scale)

The loader is read-only and idempotent. Missing fixture = empty metrics
(graceful fallback, no exceptions raised to callers).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False


@dataclass
class AppCriticalDensity:
    app: str
    label: str = ""
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    blocker_issues: int = 0
    critical_density_pct: float = 0.0
    hosting: str = ""
    notes: str = ""


@dataclass
class PriorityHint:
    app: str
    priority_score: float = 0.0
    rationale: str = ""


@dataclass
class SystemicPattern:
    pattern: str
    prevalence: str = ""
    prevalence_pct: float | None = None
    count: int | None = None
    note: str = ""


@dataclass
class LegalSignals:
    nda_signed_date: str = ""
    nda_status: str = ""
    renewal_required_before_transfer: bool = False
    nda_notes: str = ""


@dataclass
class CommercialSignals:
    facturacion_usd: float = 0.0
    contract_coverage_pct: float = 100.0
    uncovered_spend_usd: float = 0.0
    invoices_total: int = 0
    contracts_total: int = 0
    paraguas_contract_name: str = ""
    paraguas_contract_signed_year: int = 0
    bpo_size_min: int = 0
    bpo_size_max: int = 0
    client_revenue_share_of_vendor_pct: float = 0.0


@dataclass
class EcosystemMetrics:
    """Aggregated view of the tenant-alpha-ecosystem-health.yaml fixture."""

    version: str = ""
    tenant_id: str = ""

    # Ecosystem-wide
    total_loc: int = 0
    total_apps: int = 0
    total_components: int = 0
    total_issues: int = 0
    satellite_issues: int = 0
    core_cobol_issues: int = 0
    critical_issues: int = 0
    critical_density_pct: float = 0.0
    apps_without_tests: int = 0
    apps_without_cicd: int = 0
    sql_concat_queries: int = 0
    tables_without_fk_pct: float = 0.0
    pii_items: int = 0
    pii_inputs: int = 0
    db_growth_monthly_pct: float = 0.0

    # Risk exposure
    risk_reputational_usd: float = 0.0
    risk_pii_usd: float = 0.0
    risk_integrity_usd: float = 0.0
    risk_total_usd: float = 0.0
    risk_basis: str = ""

    # Commercial + legal
    commercial: CommercialSignals = field(default_factory=CommercialSignals)
    legal: LegalSignals = field(default_factory=LegalSignals)

    # Per-app + systemic
    per_app: list[AppCriticalDensity] = field(default_factory=list)
    systemic_patterns: list[SystemicPattern] = field(default_factory=list)
    priority_hints: list[PriorityHint] = field(default_factory=list)

    _loaded: bool = False

    def is_loaded(self) -> bool:
        return self._loaded

    def app(self, codename: str) -> AppCriticalDensity | None:
        for a in self.per_app:
            if a.app == codename:
                return a
        return None

    def priority_hint(self, codename: str) -> PriorityHint | None:
        for p in self.priority_hints:
            if p.app == codename:
                return p
        return None

    def ranked_by_priority(self) -> list[PriorityHint]:
        return sorted(self.priority_hints, key=lambda p: p.priority_score, reverse=True)

    def summary(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "tenant_id": self.tenant_id,
            "loaded": self._loaded,
            "total_loc": self.total_loc,
            "total_apps": self.total_apps,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "critical_density_pct": self.critical_density_pct,
            "risk_total_usd": self.risk_total_usd,
            "commercial_contract_coverage_pct": self.commercial.contract_coverage_pct,
            "per_app_count": len(self.per_app),
            "priority_hints_count": len(self.priority_hints),
        }


def _default_fixture_path() -> Path:
    return (
        Path(__file__).parent / "fixtures" / "tenant-alpha-ecosystem-health.yaml"
    )


def load_ecosystem_metrics(path: str | Path | None = None) -> EcosystemMetrics:
    """Load the ecosystem health YAML and produce an ``EcosystemMetrics``.

    Args:
        path: optional override. If None, uses the bundled fixture at
            ``app/synth/fixtures/tenant-alpha-ecosystem-health.yaml``.

    Returns:
        A populated ``EcosystemMetrics`` (with ``is_loaded=True``) on
        success, or an empty ``EcosystemMetrics`` when the fixture is
        missing or YAML cannot be parsed. Never raises to the caller.
    """
    metrics = EcosystemMetrics()
    if not _YAML_AVAILABLE:
        logger.warning("PyYAML not installed — ecosystem metrics disabled")
        return metrics

    target = Path(path) if path else _default_fixture_path()
    if not target.is_file():
        logger.info("Ecosystem metrics fixture not found at %s", target)
        return metrics

    try:
        data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning("Failed to parse ecosystem metrics %s: %s", target, exc)
        return metrics

    metrics.version = str(data.get("version", ""))
    metrics.tenant_id = str(data.get("tenant_id", ""))

    eco = data.get("ecosystem") or {}
    metrics.total_loc = int(eco.get("total_loc", 0) or 0)
    metrics.total_apps = int(eco.get("total_apps", 0) or 0)
    metrics.total_components = int(eco.get("total_components", 0) or 0)
    metrics.total_issues = int(eco.get("total_issues", 0) or 0)
    metrics.satellite_issues = int(eco.get("satellite_issues", 0) or 0)
    metrics.core_cobol_issues = int(eco.get("core_cobol_issues", 0) or 0)
    metrics.critical_issues = int(eco.get("critical_issues", 0) or 0)
    metrics.critical_density_pct = float(eco.get("critical_density_pct", 0.0) or 0.0)
    metrics.apps_without_tests = int(eco.get("apps_without_tests", 0) or 0)
    metrics.apps_without_cicd = int(eco.get("apps_without_cicd", 0) or 0)
    metrics.sql_concat_queries = int(eco.get("sql_concat_queries", 0) or 0)
    metrics.tables_without_fk_pct = float(eco.get("tables_without_fk_pct", 0.0) or 0.0)
    metrics.pii_items = int(eco.get("pii_items", 0) or 0)
    metrics.pii_inputs = int(eco.get("pii_inputs", 0) or 0)
    metrics.db_growth_monthly_pct = float(eco.get("db_growth_monthly_pct", 0.0) or 0.0)

    risk = data.get("risk_exposure_usd") or {}
    metrics.risk_reputational_usd = float(risk.get("reputational", 0.0) or 0.0)
    metrics.risk_pii_usd = float(risk.get("pii", 0.0) or 0.0)
    metrics.risk_integrity_usd = float(risk.get("integrity", 0.0) or 0.0)
    metrics.risk_total_usd = float(risk.get("total", 0.0) or 0.0)
    metrics.risk_basis = str(risk.get("basis", ""))

    comm = data.get("commercial") or {}
    c = CommercialSignals(
        facturacion_usd=float(comm.get("platform_vendor_facturacion_usd", 0.0) or 0.0),
        contract_coverage_pct=float(comm.get("contract_coverage_pct", 100.0) or 100.0),
        uncovered_spend_usd=float(comm.get("uncovered_spend_usd", 0.0) or 0.0),
        invoices_total=int(comm.get("invoices_total", 0) or 0),
        contracts_total=int(comm.get("contracts_total", 0) or 0),
        bpo_size_min=int(comm.get("bpo_size_min", 0) or 0),
        bpo_size_max=int(comm.get("bpo_size_max", 0) or 0),
        client_revenue_share_of_vendor_pct=float(
            comm.get("client_revenue_share_of_vendor_pct", 0.0) or 0.0
        ),
    )
    paraguas = comm.get("paraguas_contract") or {}
    c.paraguas_contract_name = str(paraguas.get("name", ""))
    c.paraguas_contract_signed_year = int(paraguas.get("signed_year", 0) or 0)
    metrics.commercial = c

    legal = data.get("legal") or {}
    nda = legal.get("nda") or {}
    metrics.legal = LegalSignals(
        nda_signed_date=str(nda.get("signed_date", "")),
        nda_status=str(nda.get("status", "")),
        renewal_required_before_transfer=bool(
            nda.get("renewal_required_before_transfer", False)
        ),
        nda_notes=str(nda.get("notes", "")).strip(),
    )

    for row in (data.get("per_app_critical") or []):
        if not isinstance(row, dict) or "app" not in row:
            continue
        metrics.per_app.append(AppCriticalDensity(
            app=row["app"],
            label=row.get("label", ""),
            total_issues=int(row.get("total_issues", 0) or 0),
            critical_issues=int(row.get("critical_issues", 0) or 0),
            high_issues=int(row.get("high_issues", 0) or 0),
            blocker_issues=int(row.get("blocker_issues", 0) or 0),
            critical_density_pct=float(row.get("critical_density_pct", 0.0) or 0.0),
            hosting=row.get("hosting", ""),
            notes=row.get("notes", ""),
        ))

    for row in (data.get("systemic_patterns") or []):
        if not isinstance(row, dict) or "pattern" not in row:
            continue
        metrics.systemic_patterns.append(SystemicPattern(
            pattern=row["pattern"],
            prevalence=str(row.get("prevalence", "")),
            prevalence_pct=row.get("prevalence_pct"),
            count=row.get("count"),
            note=row.get("note", ""),
        ))

    for row in (data.get("priority_hints") or []):
        if not isinstance(row, dict) or "app" not in row:
            continue
        metrics.priority_hints.append(PriorityHint(
            app=row["app"],
            priority_score=float(row.get("priority_score", 0.0) or 0.0),
            rationale=str(row.get("rationale", "")),
        ))

    metrics._loaded = True
    logger.info(
        "Ecosystem metrics loaded: %d apps, %d priority hints, %d patterns",
        len(metrics.per_app), len(metrics.priority_hints),
        len(metrics.systemic_patterns),
    )
    return metrics
