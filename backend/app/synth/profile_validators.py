"""Pydantic validators for the tenant-profile YAML boundary.

Parallel module (Ruta B): `profile.py` (dataclasses) is untouched. These
Pydantic models mirror every dataclass shape in `profile.py` and validate
the **raw YAML dict** before `load_profile` constructs dataclasses from it.

Why this exists:
    - `profile.py` is an encapsulated component; per CLAUDE.md, we add
      alongside rather than modify.
    - `load_profile` uses `.get(..., default)` which silently swallows
      typos and type errors (e.g. `orchestator` instead of `orchestrator`,
      or a string where a list is expected).
    - Pydantic v2 catches those at the boundary with a clear error path.

Opt-in usage:
    >>> from app.synth.profile_validators import load_profile_validated
    >>> profile = load_profile_validated("path/to/tenant.yaml")

`load_profile_validated` validates, then delegates to the existing
`load_profile` so downstream code keeps receiving real dataclass
instances. If validation fails, `pydantic.ValidationError` is raised with
a precise JSON-pointer-style path to the offending field.

Type policy:
    - `strict=False`: allows int→float coercion (monetary fields) and
      YAML's natural typing. Still catches list-where-dict and similar.
    - `extra='ignore'`: matches `load_profile`'s tolerant behavior today.
      Tighten to 'forbid' once we've audited all fixtures for typos.
    - `Literal[...]` on categorical fields: catches typos in enum-like
      strings (e.g. `orchestrator`, `action`, `nda_status`). This is the
      single biggest bug-reduction lever Pydantic unlocks here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.synth.profile import TenantProfile, load_profile


# ─── shared config ──────────────────────────────────────────────────

_STRICT_CONFIG = ConfigDict(
    strict=False,       # let int↔float coerce naturally (money, ratios)
    extra="ignore",     # mirrors `.get(..., default)` tolerance in load_profile
    frozen=False,       # validators build, then dataclasses consume
)


class _SchemaBase(BaseModel):
    model_config = _STRICT_CONFIG


# ─── leaf schemas ───────────────────────────────────────────────────

class VulnerabilityDensitySchema(_SchemaBase):
    sql_injection: int = 0
    hardcoded_creds: int = 0
    weak_crypto: int = 0
    command_injection: int = 0
    missing_fk: int = 0
    pii_leak: int = 0
    suppressed_exceptions: int = 0


class DatabaseSpecSchema(_SchemaBase):
    engine: Literal["sqlserver", "mysql", "db2", "oracle", "sqlite", "redis", "postgres", "aurora"]
    tables: int = 20
    pii_columns: int = 5


class OperationalWindowSchema(_SchemaBase):
    start: str = ""
    end: str = ""
    region: str = ""


class OperationalProfileSchema(_SchemaBase):
    user_count: int = 0
    user_roles: list[str] = Field(default_factory=list)
    daily_request_volume: int = 0
    historical_volume: int = 0
    operational_windows: list[OperationalWindowSchema] = Field(default_factory=list)
    vpn_required: bool = False
    mfa_required: bool = False
    planned_integrations: list[str] = Field(default_factory=list)


class SubProjectSchema(_SchemaBase):
    name: str
    language: Literal[
        "csharp", "python", "vbnet", "java", "php",
        "typescript", "javascript", "cobol", "cpp", "go", "ruby",
    ]
    loc_share: float = 1.0
    vuln_share: float = 1.0
    modules: int = 6
    has_rpa: bool = False
    operational: OperationalProfileSchema | None = None


class MultiRobotPipelineSchema(_SchemaBase):
    robot_count: int = 1
    coordination: Literal["zmq-broker", "kafka", "redis-queue", "direct-rpc", "none", ""] = "none"
    stages: list[str] = Field(default_factory=list)
    compensation_transactions: bool = False
    failure_detection: Literal["none", "heartbeat", "timeout", "health-check", ""] = "none"
    scraping_based: bool = False
    upstream_ui_owner: str = ""
    broker_location: str = ""
    schedule: str = ""


class RefactorDecisionSchema(_SchemaBase):
    action: Literal["refactor", "retire", "retain", "tbd", "gate"] = "refactor"
    phase: str = "Q3"
    rationale: str = ""
    validation_checklist: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    gate_type: str = ""
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    blocker_to_resolve: str = ""
    estimated_savings_if_taken: str = ""
    stakeholders_to_confirm: list[str] = Field(default_factory=list)


class ExposureProfileSchema(_SchemaBase):
    surface: Literal["public-internet", "private-vpn", "internal-only", "aws-private"] = "internal-only"
    dual_backend: bool = False
    auth_layers: list[str] = Field(default_factory=list)
    edge_protection: Literal["waf", "api-gateway", "none"] = "none"
    geo_restrictions: list[str] = Field(default_factory=list)
    user_count: int = 0
    mfa_required: bool = False


class RegionalPolicySchema(_SchemaBase):
    region_scope: Literal["country", "zone", "iata-area"] = "country"
    regions: list[str] = Field(default_factory=list)
    policy_type: str = ""
    externalization: Literal[
        "hardcoded", "config-file", "rules-engine", "external-service", "unknown"
    ] = "unknown"
    owner: str = ""


class AppRecipeSchema(_SchemaBase):
    codename: str
    label: str
    loc_target: int = 50_000
    primary_language: Literal[
        "csharp", "python", "vbnet", "java", "php",
        "typescript", "javascript", "cobol", "cpp", "go", "ruby",
    ]
    additional_languages: list[str] = Field(default_factory=list)
    databases: list[DatabaseSpecSchema] = Field(default_factory=list)
    vulnerabilities: VulnerabilityDensitySchema = Field(default_factory=VulnerabilityDensitySchema)
    has_cobol_layer: bool = False
    is_shared_nexus: bool = False
    has_rpa: bool = False
    modules: int = 10
    sub_projects: list[SubProjectSchema] = Field(default_factory=list)
    db_inactive_since: str = ""
    decision: RefactorDecisionSchema | None = None
    inject_legacy_db_schema: bool = False
    inject_god_method_cc: int = 0
    multi_robot: MultiRobotPipelineSchema | None = None
    exposure: ExposureProfileSchema | None = None
    regional_policies: list[RegionalPolicySchema] = Field(default_factory=list)


# ─── compliance ──────────────────────────────────────────────────────

class ComplianceCertificationSchema(_SchemaBase):
    name: str
    framework: str = ""
    due_date: str = ""
    # `non_compliant` was added in the Gap G enrichment (2026-04-12) but the
    # dataclass docstring in profile.py still lists only 4 values — the
    # validator surfaced this drift on first run. Kept in sync with fixture
    # reality; tighten back after the dataclass docstring is updated.
    status: Literal[
        "in_progress", "at_risk", "blocked", "complete", "non_compliant",
    ] = "in_progress"
    owner: str = "compliance"
    description: str = ""


class ModernizationPhaseSchema(_SchemaBase):
    name: str
    start_date: str = ""
    end_date: str = ""
    milestones: list[str] = Field(default_factory=list)


class ComplianceProfileSchema(_SchemaBase):
    hard_deadline: str = ""
    certifications: list[ComplianceCertificationSchema] = Field(default_factory=list)
    phases: list[ModernizationPhaseSchema] = Field(default_factory=list)
    audit_cadence: str = ""
    narrative: str = ""


# ─── commercial risk / legal ────────────────────────────────────────

class VendorDependencySchema(_SchemaBase):
    name: str
    category: Literal["legacy-platform", "consulting", "cloud", "saas", "audit"] = "saas"
    revenue_share_pct: float = 0.0
    spend_2y_usd: float = 0.0
    contract_coverage_pct: float = 100.0
    lock_in_level: Literal["low", "medium", "high", "critical"] = "medium"
    notes: str = ""


class PenaltyExposureSchema(_SchemaBase):
    category: Literal["reputational", "privacy", "integrity", "regulatory"]
    cap_usd: float = 0.0
    driver: str = ""


class LegalRiskSchema(_SchemaBase):
    nda_signed_date: str = ""
    nda_status: Literal["current", "possibly-expired", "expired", "missing"] = "current"
    nda_renewal_required: bool = False
    nda_notes: str = ""
    contract_coverage_pct: float = 100.0
    uncovered_spend_usd: float = 0.0
    paraguas_contract_name: str = ""
    paraguas_contract_signed_year: int = 0


class CommercialRiskProfileSchema(_SchemaBase):
    vendors: list[VendorDependencySchema] = Field(default_factory=list)
    penalty_exposure: list[PenaltyExposureSchema] = Field(default_factory=list)
    contract_gap_pct: float = 0.0
    total_exposure_usd: float = 0.0
    narrative: str = ""
    legal_risk: LegalRiskSchema | None = None


# ─── governance ──────────────────────────────────────────────────────

class GovernanceTeamSchema(_SchemaBase):
    name: str
    role: Literal[
        "primary-delivery", "parallel-delivery", "steering", "audit", "external-vendor",
    ] = "primary-delivery"
    app_scope: list[str] = Field(default_factory=list)
    headcount: int = 0
    status: Literal["active", "forming", "ramping", "exiting"] = "active"


class SteeringCommitteeSchema(_SchemaBase):
    cadence: str = ""
    attendees: list[str] = Field(default_factory=list)
    owner_role: str = ""
    first_formal_review: str = ""


class CodeAccessGateSchema(_SchemaBase):
    model: Literal["direct", "pr-only", "intermediate-reviewer", "sandbox-only"] = "direct"
    owner_role: str = ""
    bottleneck: bool = False
    notes: str = ""


class TechLeadRoleSchema(_SchemaBase):
    status: Literal["unfilled", "recruiting", "hired", "onboarding"] = "unfilled"
    scope: str = ""
    target_start_date: str = ""


class GovernanceProfileSchema(_SchemaBase):
    steering: SteeringCommitteeSchema | None = None
    teams: list[GovernanceTeamSchema] = Field(default_factory=list)
    code_access: CodeAccessGateSchema | None = None
    tech_lead: TechLeadRoleSchema | None = None
    raci_summary: str = ""
    narrative: str = ""


# ─── discovery-sourced profiles ─────────────────────────────────────

class PlatformVendorSchema(_SchemaBase):
    name: str = ""
    surface_area: list[str] = Field(default_factory=list)
    lock_in_level: Literal["low", "medium", "high", "critical"] = "high"
    exit_plan: str = ""
    dependent_apps: list[str] = Field(default_factory=list)
    controls_production: bool = True
    controls_credentials: bool = True
    sla_hours: int = 24


class EdgeSecuritySchema(_SchemaBase):
    waf_present: bool = False
    waf_provider: Literal["corporate", "aws-waf", "cloudflare", "none"] = "none"
    geo_blocking: list[str] = Field(default_factory=list)
    pattern_rules: list[str] = Field(default_factory=list)
    scan_cadence: Literal["continuous", "periodic", "on-demand", "none"] = "none"
    remediation_channel: Literal[
        "bidirectional-informal", "formal-tickets", "none",
    ] = "none"


class InfrastructureRiskSchema(_SchemaBase):
    orchestrator: Literal["none", "control-m", "airflow", "manual"] = "none"
    blueprint_exists: bool = True
    server_model: str = ""
    server_count: int = 1
    environments_on_same_server: bool = False
    redundancy_type: Literal["none", "active-passive", "cloud-native"] = "none"
    capacity_planning_freq: str = "annual"
    edge_security: EdgeSecuritySchema | None = None


class SecretManagementSchema(_SchemaBase):
    product: Literal[
        "hashicorp-vault", "aws-secrets-manager", "azure-keyvault",
        "env-vars", "config-files",
    ] = "env-vars"
    internal_alias: str = ""
    scope: Literal["per-app", "shared-vault", "none"] = "per-app"
    rotation_policy: Literal["automatic", "manual", "none"] = "manual"
    hash_based_injection: bool = False
    on_premise: bool = False
    rotates_users: bool = False
    rotates_db_creds: bool = False


class ModernizationProgramSchema(_SchemaBase):
    name: str = ""
    total_apps: int = 0
    migrated_apps: int = 0
    strategies: list[str] = Field(default_factory=list)
    activities_per_app: int = 0
    tier_classification: dict[str, Any] = Field(default_factory=dict)
    scope_apps_status: dict[str, Any] = Field(default_factory=dict)


class ThirdPartyDepSchema(_SchemaBase):
    name: str
    role: Literal[
        "rpa-operator", "dev-contractor", "infra-provider", "unknown",
    ] = "unknown"
    documented: bool = False
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    apps_affected: list[str] = Field(default_factory=list)


class NonScopeAppStubSchema(_SchemaBase):
    codename: str
    label: str = ""
    category: Literal[
        "satellite", "shared-library", "archival", "utility", "integration",
    ] = "satellite"
    notes: str = ""


# ─── top-level tenant profile ───────────────────────────────────────

class TenantProfileSchema(_SchemaBase):
    tenant_id: str
    display_name: str
    seed: int = 42
    apps: list[AppRecipeSchema] = Field(default_factory=list)
    description: str = ""
    compliance: ComplianceProfileSchema | None = None
    commercial_risk: CommercialRiskProfileSchema | None = None
    governance: GovernanceProfileSchema | None = None
    platform_vendor: PlatformVendorSchema | None = None
    infrastructure_risk: InfrastructureRiskSchema | None = None
    modernization_program: ModernizationProgramSchema | None = None
    orchestration_model: Literal[
        "none", "manual", "semi-auto", "fully-orchestrated", "unknown",
    ] = "unknown"
    third_party_deps: list[ThirdPartyDepSchema] = Field(default_factory=list)
    secret_management: SecretManagementSchema | None = None
    non_scope_apps: list[NonScopeAppStubSchema | str] = Field(default_factory=list)


# ─── public entry points ────────────────────────────────────────────

def validate_tenant_yaml(raw: dict[str, Any]) -> TenantProfileSchema:
    """Validate a raw YAML dict against the tenant-profile schema.

    Raises `pydantic.ValidationError` with a precise path to the
    offending field when the YAML is malformed.
    """
    return TenantProfileSchema.model_validate(raw)


def load_profile_validated(path: str | Path) -> TenantProfile:
    """Parse YAML, validate with Pydantic, then build the existing
    `TenantProfile` dataclass via the original `load_profile`.

    On validation failure this raises `pydantic.ValidationError`
    *before* any dataclass construction happens, so partial state is
    impossible. On success, the returned dataclass is byte-for-byte
    identical to what `load_profile(path)` would have produced.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Tenant profile fixture not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    validate_tenant_yaml(raw)
    return load_profile(path)
