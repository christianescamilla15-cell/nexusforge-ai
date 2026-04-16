"""Profile data classes for synthetic tenant generation.

A TenantProfile holds the overall parameters for a tenant showcase. Each
AppRecipe describes one synthetic application inside that tenant.

Profiles are loaded from YAML fixtures under ``fixtures/``. They are
deterministic: the same profile + seed always produces the same output.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class VulnerabilityDensity:
    """Per-app vulnerability injection density.

    Values are absolute counts. The generator inserts exactly this many
    instances of each pattern into the generated code so the refactor
    engine's detectors find predictable numbers.
    """

    sql_injection: int = 0
    hardcoded_creds: int = 0
    weak_crypto: int = 0
    command_injection: int = 0
    missing_fk: int = 0
    pii_leak: int = 0
    suppressed_exceptions: int = 0

    def total(self) -> int:
        return (
            self.sql_injection
            + self.hardcoded_creds
            + self.weak_crypto
            + self.command_injection
            + self.missing_fk
            + self.pii_leak
            + self.suppressed_exceptions
        )


@dataclass
class DatabaseSpec:
    """Describes a database this app talks to."""

    engine: str  # sqlserver, mysql, db2, oracle, sqlite, redis
    tables: int = 20
    pii_columns: int = 5


@dataclass
class OperationalWindow:
    """One operational time window for an app (P-012).

    Captures the time-of-day + region pattern used by apps like
    ``app-03-special`` where throughput is bounded to working hours.
    Used by the strangler planner to schedule refactor work outside
    active windows (no user impact) and by the capacity planner.
    """

    start: str = ""     # HH:MM (24h)
    end: str = ""       # HH:MM (24h)
    region: str = ""    # optional ISO code or region tag


@dataclass
class OperationalProfile:
    """Operational metrics for an app (P-012).

    Models the empirical scale signals captured in workshops / BIAs:
    how many authorized users, daily request volume, and which
    windows are active. Attached optionally to a SubProject so a
    mega-app like ``app-03`` can model per-flow operational density
    (ARC is public, Especiales has 81 users in 4 windows, BSP runs on
    a schedule without an interactive user pool).

    Sourced from H-140 (workshop W2, Reembolsos Especiales) + BIA BSP.
    """

    user_count: int = 0
    user_roles: list[str] = field(default_factory=list)
    daily_request_volume: int = 0
    historical_volume: int = 0           # lifetime/since-inception totals
    operational_windows: list[OperationalWindow] = field(default_factory=list)
    vpn_required: bool = False
    mfa_required: bool = False
    planned_integrations: list[str] = field(default_factory=list)  # e.g. ["ram-refunds"]


@dataclass
class SubProject:
    """One sub-project inside an app.

    Real enterprise legacy apps are usually bundles of 3-4 sub-projects
    with different stacks (e.g., a Java backend + Python RPA robot +
    TypeScript frontend). The synth generator treats each sub-project
    as a distinct directory with its own language and vulnerability
    share.
    """

    name: str  # e.g., "backend", "rpa-robot", "frontend"
    language: str  # csharp, python, vbnet, java, php, typescript, cobol
    loc_share: float = 1.0  # fraction of parent app's LOC budget (sum across sub-projects should be ~1.0)
    vuln_share: float = 1.0  # fraction of parent app's vulnerability budget
    modules: int = 6  # modules to generate inside this sub-project
    has_rpa: bool = False  # if True, use the RPA-flavoured templates
    # P-012 (2026-04-13) — optional operational profile (81 users, ventanas, VPN, ...).
    operational: OperationalProfile | None = None


@dataclass
class MultiRobotPipeline:
    """Orchestrated multi-robot pipeline pattern (P-019).

    Models systems like ``app-03-bsp`` where multiple robots communicate
    via a message broker to implement a staged workflow (e.g., download →
    validate → respond). Captures risk signals the strangler planner
    considers when prioritizing refactor phases:

    - ``compensation_transactions=False`` means partial failures leave
      the system in an inconsistent state — HIGH risk.
    - ``scraping_based=True`` (Playwright/Selenium against a third-party
      UI) means cosmetic changes to the upstream UI break the pipeline —
      HIGH risk + calls for contract tests.
    - ``failure_detection="none"`` means silent failures possible.

    This dataclass is optional on ``AppRecipe``. When absent, the app
    follows the default single-module refactor flow.
    """

    robot_count: int = 1
    coordination: str = "none"           # "zmq-broker" | "kafka" | "redis-queue" | "direct-rpc" | "none"
    stages: list[str] = field(default_factory=list)  # ordered stage names
    compensation_transactions: bool = False
    failure_detection: str = "none"      # "none" | "heartbeat" | "timeout" | "health-check"
    scraping_based: bool = False         # True if uses Playwright/Selenium against external UI
    upstream_ui_owner: str = ""          # free text, e.g. "external-iata-bsplink"
    broker_location: str = ""            # where the broker runs (hostname, container, etc.)
    schedule: str = ""                   # free text, e.g., "every 4h 08-20"

    def risk_level(self) -> str:
        """Heuristic risk classification based on signals."""
        signals = 0
        if not self.compensation_transactions and self.robot_count > 1:
            signals += 2  # partial failures leave state inconsistent
        if self.scraping_based:
            signals += 2  # fragile to upstream UI changes
        if self.failure_detection in ("none", ""):
            signals += 1  # silent failures possible
        if self.coordination in ("none", ""):
            signals += 1  # no explicit coordination layer
        if signals >= 4:
            return "high"
        if signals >= 2:
            return "medium"
        return "low"

    def recommendations(self) -> list[str]:
        """Concrete refactor recommendations derived from the risk signals."""
        recs: list[str] = []
        if not self.compensation_transactions and self.robot_count > 1:
            recs.append(
                "Add compensation transactions between robots so partial "
                "failures can roll back cleanly."
            )
        if self.scraping_based and self.upstream_ui_owner:
            recs.append(
                f"Add contract tests against the upstream UI owner "
                f"'{self.upstream_ui_owner}' to detect selector regressions."
            )
        if self.failure_detection in ("none", ""):
            recs.append(
                "Add inter-robot health-check + alerting so silent failures "
                "surface within one pipeline cycle."
            )
        if self.coordination in ("none", "") and self.robot_count > 1:
            recs.append(
                "Introduce an explicit message broker (Redis/Kafka/ZMQ) so "
                "coordination is observable and replayable."
            )
        return recs


@dataclass
class RefactorDecision:
    """Pre-assigned migration decision for an app.

    Emitted by the Plan Componer Deuda pattern: classify each app as
    REFACTOR / RETIRE / RETAIN / TBD and the strangler planner should
    honor the classification instead of making its own call.
    """

    action: str = "refactor"  # refactor, retire, retain, tbd
    phase: str = "Q3"  # Q1..Q4, IMMEDIATE, TBD
    rationale: str = ""
    validation_checklist: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    # P-018 / Gap T (2026-04-13) — decision-gate framework.
    # When an action is contested (typically ``tbd`` / ``gate``), these
    # fields capture the evidence on each side of the decision plus the
    # blocker that must be resolved before the team commits. The
    # strangler planner surfaces this structure in the plan narrative so
    # stakeholders see the pending call explicitly instead of an
    # opaque "tbd".
    #
    # Sourced from H-149 (app-03-arc 0% activity since 2023 → audit-vendor
    # recommends RETIRE, business owner not confirmed).
    gate_type: str = ""                                    # e.g. "retire-vs-refactor" | ""
    evidence_for: list[str] = field(default_factory=list)  # data supporting action
    evidence_against: list[str] = field(default_factory=list)  # data against action
    blocker_to_resolve: str = ""                           # single highest-priority blocker
    estimated_savings_if_taken: str = ""                   # free text (effort, infra, etc.)
    stakeholders_to_confirm: list[str] = field(default_factory=list)  # roles/people to ping

    @property
    def is_gate(self) -> bool:
        """True when this decision is waiting on stakeholder input."""
        return bool(self.gate_type) or self.action.lower() in ("tbd", "gate")

    def to_markdown(self, app_codename: str, app_label: str) -> str:
        checklist = "\n".join(f"- [ ] {item}" for item in self.validation_checklist) or "- (none)"
        blockers = "\n".join(f"- {item}" for item in self.blockers) or "- (none)"
        md = (
            f"# Refactor Decision — `{app_codename}`\n\n"
            f"**App:** {app_label}\n"
            f"**Action:** `{self.action.upper()}`\n"
            f"**Phase:** {self.phase}\n\n"
            f"## Rationale\n\n{self.rationale or '(no rationale provided)'}\n\n"
            f"## Validation checklist\n\n{checklist}\n\n"
            f"## Blockers\n\n{blockers}\n\n"
        )
        if self.is_gate:
            ev_for = "\n".join(f"- {e}" for e in self.evidence_for) or "- (none)"
            ev_against = "\n".join(f"- {e}" for e in self.evidence_against) or "- (none)"
            stakeholders = ", ".join(self.stakeholders_to_confirm) or "(not specified)"
            md += (
                f"## Decision gate — `{self.gate_type or self.action}`\n\n"
                f"**Evidence FOR the proposed action:**\n{ev_for}\n\n"
                f"**Evidence AGAINST (blockers for the action):**\n{ev_against}\n\n"
                f"**Blocker to resolve:** {self.blocker_to_resolve or '(not specified)'}\n\n"
                f"**Estimated savings if taken:** {self.estimated_savings_if_taken or '(not quantified)'}\n\n"
                f"**Stakeholders to confirm:** {stakeholders}\n\n"
            )
        md += (
            f"_Auto-generated by synth. The strangler planner reads this file "
            f"and honors the action / phase when present._\n"
        )
        return md


@dataclass
class AppRecipe:
    """One synthetic application inside a tenant."""

    codename: str  # e.g., "app-01"
    label: str  # user-facing display, e.g., "Transaction Reconciliation Service"
    loc_target: int  # approximate lines of code
    primary_language: str  # csharp, python, vbnet, java, php, typescript, cobol, cpp
    additional_languages: list[str] = field(default_factory=list)
    databases: list[DatabaseSpec] = field(default_factory=list)
    vulnerabilities: VulnerabilityDensity = field(default_factory=VulnerabilityDensity)
    has_cobol_layer: bool = False
    is_shared_nexus: bool = False  # if True, other apps will import from this
    has_rpa: bool = False  # if True, include Playwright/Selenium fragile selectors
    modules: int = 10  # number of sub-modules to generate (single-project mode)
    sub_projects: list[SubProject] = field(default_factory=list)
    db_inactive_since: str = ""  # ISO date — if set, triggers retirement-path logic
    decision: RefactorDecision | None = None
    inject_legacy_db_schema: bool = False  # if True, generate a SQL dump fixture with 0-FK legacy schema
    inject_god_method_cc: int = 0  # if > 0, emit a god method with ~this cyclomatic complexity
    multi_robot: MultiRobotPipeline | None = None  # P-019 — present for systems like app-03-bsp
    exposure: ExposureProfile | None = None  # P-009 — network exposure profile (public/vpn/internal)
    regional_policies: list[RegionalPolicy] = field(default_factory=list)  # P-014 — per-region business rules

    @property
    def all_languages(self) -> list[str]:
        seen = [self.primary_language]
        for lang in self.additional_languages:
            if lang not in seen:
                seen.append(lang)
        if self.has_cobol_layer and "cobol" not in seen:
            seen.append("cobol")
        for sub in self.sub_projects:
            if sub.language not in seen:
                seen.append(sub.language)
        return seen

    @property
    def is_multi_project(self) -> bool:
        return bool(self.sub_projects)


@dataclass
class ComplianceCertification:
    """One regulatory certification or audit the tenant must achieve."""

    name: str  # e.g., "SOC 2 Type II"
    framework: str  # e.g., "AICPA Trust Services Criteria"
    due_date: str  # ISO date, e.g., "2026-09-30"
    status: str = "in_progress"  # in_progress / at_risk / blocked / complete
    owner: str = "compliance"  # team that owns this certification
    description: str = ""


@dataclass
class ModernizationPhase:
    """One phase in the modernization roadmap with start/end dates."""

    name: str  # e.g., "Discovery", "Execution", "Testing + UAT"
    start_date: str  # ISO date
    end_date: str  # ISO date
    milestones: list[str] = field(default_factory=list)


@dataclass
class ComplianceProfile:
    """Tenant-wide compliance and deadline metadata.

    Loaded from an optional ``compliance`` block in the tenant YAML
    fixture. Used by the /showcase frontend to render a countdown to
    the hard deadline and a readiness summary for each certification.
    """

    hard_deadline: str = ""  # ISO date — the single go-live commitment
    certifications: list[ComplianceCertification] = field(default_factory=list)
    phases: list[ModernizationPhase] = field(default_factory=list)
    audit_cadence: str = ""  # e.g., "Monthly steering committee, day 14"
    narrative: str = ""  # short stakeholder-facing summary

    def to_dict(self) -> dict:
        return {
            "hard_deadline": self.hard_deadline,
            "certifications": [asdict(c) for c in self.certifications],
            "phases": [asdict(p) for p in self.phases],
            "audit_cadence": self.audit_cadence,
            "narrative": self.narrative,
        }


@dataclass
class VendorDependency:
    """One external vendor the tenant depends on."""

    name: str  # codename only, e.g., "legacy-platform-vendor"
    category: str  # legacy-platform / consulting / cloud / saas / audit
    revenue_share_pct: float = 0.0  # how much of vendor's revenue comes from this tenant
    spend_2y_usd: float = 0.0  # 2-year spend with this vendor in USD
    contract_coverage_pct: float = 100.0  # % of spend under a written contract
    lock_in_level: str = "medium"  # low / medium / high
    notes: str = ""


@dataclass
class PenaltyExposure:
    """Upper-bound penalty scenarios."""

    category: str  # reputational / privacy / integrity / regulatory
    cap_usd: float  # worst-case dollar cap
    driver: str = ""  # short sentence describing the trigger


@dataclass
class GovernanceTeam:
    """One team involved in the modernization program."""

    name: str  # codename only (e.g., "team-primary", "team-secondary")
    role: str  # primary-delivery / parallel-delivery / steering / audit / external-vendor
    app_scope: list[str] = field(default_factory=list)  # codenames of apps this team owns
    headcount: int = 0
    status: str = "active"  # active / forming / ramping / exiting


@dataclass
class SteeringCommittee:
    """Governance committee configuration."""

    cadence: str = ""  # e.g., "Monthly, day 14"
    attendees: list[str] = field(default_factory=list)  # role names only
    owner_role: str = ""  # chair
    first_formal_review: str = ""  # ISO date


@dataclass
class CodeAccessGate:
    """Who controls write access to the target repositories."""

    model: str = "direct"  # direct / pr-only / intermediate-reviewer / sandbox-only
    owner_role: str = ""  # e.g., "legacy-vendor-lead"
    bottleneck: bool = False  # True if this gate is a known delivery bottleneck
    notes: str = ""


@dataclass
class TechLeadRole:
    """Post-modernization tech lead slot."""

    status: str = "unfilled"  # unfilled / recruiting / hired / onboarding
    scope: str = ""  # what the tech lead will own after delivery
    target_start_date: str = ""  # ISO date


@dataclass
class GovernanceProfile:
    """Tenant-wide governance metadata.

    Captures the organizational structure around a modernization
    program: who runs the steering committee, which teams deliver
    what, how code access is gated, and the state of the post-launch
    tech lead slot. The /showcase frontend renders this as a
    governance card so stakeholders understand non-technical risk.
    """

    steering: SteeringCommittee | None = None
    teams: list[GovernanceTeam] = field(default_factory=list)
    code_access: CodeAccessGate | None = None
    tech_lead: TechLeadRole | None = None
    raci_summary: str = ""
    narrative: str = ""

    def to_dict(self) -> dict:
        return {
            "steering": asdict(self.steering) if self.steering else None,
            "teams": [asdict(t) for t in self.teams],
            "code_access": asdict(self.code_access) if self.code_access else None,
            "tech_lead": asdict(self.tech_lead) if self.tech_lead else None,
            "raci_summary": self.raci_summary,
            "narrative": self.narrative,
        }


@dataclass
class LegalRisk:
    """Legal-risk profile — P-020 / Gap R (2026-04-13).

    Captures NDA status, contract coverage, and renewal requirements.
    H-160 revealed the platform-vendor NDA may be expired since 2016
    (signed 2013-08-18, no evidence of renewal). This matters because
    the modernization implies transferring source code, credentials and
    data between parties — without a valid NDA, that transfer carries
    direct legal exposure.

    Combined with H-159 (40% of facturación without contract, $3.4M of
    uncovered spend), the legal surface is non-trivial and should
    factor into phase gating decisions.
    """

    nda_signed_date: str = ""                    # ISO date of most recent NDA signature
    nda_status: str = "current"                  # "current" | "possibly-expired" | "expired" | "missing"
    nda_renewal_required: bool = False           # True if renewal required before transfer
    nda_notes: str = ""
    contract_coverage_pct: float = 100.0         # % of spend covered by formal contract
    uncovered_spend_usd: float = 0.0             # absolute $ without coverage
    paraguas_contract_name: str = ""             # umbrella contract name
    paraguas_contract_signed_year: int = 0       # age measured for renewal planning

    def blocks_sensitive_transfer(self) -> bool:
        """True when NDA status requires escalation before transfer."""
        return self.nda_status in ("possibly-expired", "expired", "missing")


@dataclass
class CommercialRiskProfile:
    """Tenant-wide commercial risk metadata.

    Captures the non-technical factors that shape phase ordering:
    vendor concentration, contract gaps and penalty exposure. The
    strangler planner reads this profile to bring forward phases whose
    apps carry high commercial risk (e.g., hit the apps whose vendor
    contract is about to expire first).
    """

    vendors: list[VendorDependency] = field(default_factory=list)
    penalty_exposure: list[PenaltyExposure] = field(default_factory=list)
    contract_gap_pct: float = 0.0  # tenant-wide % of spend without contract coverage
    total_exposure_usd: float = 0.0  # sum of penalty caps
    narrative: str = ""
    # P-020 / Gap R (2026-04-13) — legal posture (NDA + contract coverage).
    legal_risk: LegalRisk | None = None

    def to_dict(self) -> dict:
        return {
            "vendors": [asdict(v) for v in self.vendors],
            "penalty_exposure": [asdict(p) for p in self.penalty_exposure],
            "contract_gap_pct": self.contract_gap_pct,
            "total_exposure_usd": self.total_exposure_usd,
            "narrative": self.narrative,
            "legal_risk": asdict(self.legal_risk) if self.legal_risk else None,
        }


@dataclass
class PlatformVendor:
    """A platform vendor that owns and operates part of the tenant's
    technology stack as a managed service.

    Gap C (2026-04-12) — the corpus reveals that the platform vendor
    is not just a commercial risk (already modeled in
    CommercialRiskProfile.vendors) — it is a **technical dependency**
    that controls hosting, deploys, credentials, monitoring, and
    the mainframe. The refactor engine needs to know which apps are
    hosted by the vendor, what surface area is under their control,
    and what the exit plan looks like, to produce realistic phase
    timelines.
    """

    name: str = ""                         # codename, e.g., "platform-vendor"
    surface_area: list[str] = field(default_factory=list)  # ["hosting", "deploy", "credentials", "monitoring", "mainframe"]
    lock_in_level: str = "high"            # low | medium | high | critical
    exit_plan: str = ""                    # strategy text
    dependent_apps: list[str] = field(default_factory=list)  # codenames of scope apps that depend
    controls_production: bool = True       # True = vendor owns prod deploy
    controls_credentials: bool = True      # True = vendor manages connection strings
    sla_hours: int = 24                    # incident resolution SLA in hours


@dataclass
class EdgeSecurity:
    """Edge-security profile for public-facing apps (P-011 / Gap N).

    Captures corporate WAF + geo-blocking + pattern rules that sit in
    front of public portals (e.g., ``app-03-arc``). Used by Mythos
    calibration to downgrade effective severity when a vulnerability
    is already blocked at the edge (e.g., XSS with a WAF → effective
    severity high, not critical).

    Sourced from H-119 (workshop platform-vendor 2026-04-13 W2):
    WAF blocks Rusia/Corea del Sur + SQLi/XSS patterns + rate-limiting.
    """

    waf_present: bool = False
    waf_provider: str = "none"             # "corporate" | "aws-waf" | "cloudflare" | "none"
    geo_blocking: list[str] = field(default_factory=list)  # ISO country codes, e.g. ["RU", "KP"]
    pattern_rules: list[str] = field(default_factory=list)  # e.g., ["sqli", "xss", "rate-limit"]
    scan_cadence: str = "none"             # "continuous" | "periodic" | "on-demand" | "none"
    remediation_channel: str = "none"      # "bidirectional-informal" | "formal-tickets" | "none"


@dataclass
class InfrastructureRisk:
    """Tenant-wide infrastructure risk factors.

    Gap P-005 (2026-04-12) — captures the infrastructure-level risks
    that the Report Out does not evaluate (it evaluates code, not
    operations). Sourced from discovery corpus hallazgos H-111, H-112,
    H-113: no orchestrator, no blueprint, single-server mainframe.
    """

    orchestrator: str = "none"             # "none" | "control-m" | "airflow" | "manual"
    blueprint_exists: bool = True          # False → praxis-ecosystem lost its blueprint ~2015
    server_model: str = ""                 # "IBM Power 9000" for tenant-alpha
    server_count: int = 1                  # single point of failure
    environments_on_same_server: bool = False  # True = Dev/QA/Prod on same instance
    redundancy_type: str = "none"          # "none" | "active-passive" | "cloud-native"
    capacity_planning_freq: str = "annual"

    # P-011 (2026-04-13) — edge security layer (WAF, geo-blocking).
    # Optional: when present, Mythos calibration uses it to downgrade
    # effective severity of findings that the WAF already blocks.
    edge_security: EdgeSecurity | None = None


@dataclass
class ExposureProfile:
    """Network-exposure profile for an application (P-009 / Gap N).

    Captures how a recipe is reachable from the outside world and what
    auth layers stand between the Internet and the app. Used by:

    - ``mythos-scanner`` calibration (public-internet + WAF → partial
      mitigation of XSS/SQLi findings)
    - ``strangler_planner`` phase risk scoring (public-internet apps
      get higher-risk phases up front)

    Sourced from workshop 2026-04-13 W1/W2:

    - ``app-03-arc``: public-internet portal in e-commerce cliente, has
      double back-end (public + internal-VPN), WAF edge_protection.
    - ``app-03-special``: private-vpn only, 81 users, 2FA.
    - ``app-01 (sicofav)``: aws-private (VPC), 5-6 users via VPN + 2FA.
    """

    surface: str = "internal-only"         # "public-internet" | "private-vpn" | "internal-only"
    dual_backend: bool = False             # True if public + internal-VPN back-ends (H-029)
    auth_layers: list[str] = field(default_factory=list)  # ["vpn", "2fa", "ip-whitelist", "sso"]
    edge_protection: str = "none"          # "waf" | "api-gateway" | "none"
    geo_restrictions: list[str] = field(default_factory=list)  # ISO country codes blocked
    user_count: int = 0                    # approximate authorized user pool
    mfa_required: bool = False


@dataclass
class RegionalPolicy:
    """Policy-by-region pattern (P-014 / Gap O).

    Models business rules that vary by jurisdiction — observed across
    Reembolsos flows (Brazil / Russia / north-south exceptions), Facturas
    Electrónicas (tax jurisdictions) and Medios de Pago (correspondents
    per country).

    Sourced from H-142 (workshop W1 + OBS3, reembolsos per-country rules)
    and BSPLink which operates under IATA rules per country.

    The ``externalization`` field drives refactoring recommendations:

    - ``hardcoded`` → recommend moving rules out of code (blocks expansion)
    - ``config-file`` → acceptable but not audit-friendly
    - ``rules-engine`` → target state
    - ``external-service`` → best for policy-heavy apps
    """

    region_scope: str = "country"           # "country" | "zone" | "iata-area"
    regions: list[str] = field(default_factory=list)  # ISO codes or region tags
    policy_type: str = ""                   # "refund-rules" | "tax-rules" | "payment-rules" | ...
    externalization: str = "unknown"        # "hardcoded" | "config-file" | "rules-engine" | "external-service" | "unknown"
    owner: str = ""                         # team/role responsible for rule updates

    def refactor_recommendation(self) -> str:
        """Concrete recommendation based on current externalization."""
        if self.externalization == "hardcoded":
            return (
                "Extract regional rules to external configuration. "
                "Hardcoded rules block expansion (adding a country = redeploy)."
            )
        if self.externalization == "config-file":
            return (
                "Move from config files to a versioned rules engine so "
                "changes are auditable and testable independently of deploys."
            )
        if self.externalization == "rules-engine":
            return "Target state reached — no change recommended."
        if self.externalization == "external-service":
            return "Target state reached — monitor service availability."
        return "Determine current externalization before recommending changes."


@dataclass
class SecretManagement:
    """Secret management posture for a tenant (P-010 / Gap M).

    Models HOW an app (or the tenant as a whole) handles credentials at
    runtime. This is critical for Mythos calibration: ``vault``-backed
    apps that inject secrets as runtime env vars should NOT be flagged
    as "credentials hardcoded" just because env vars appear in the
    code.

    Sourced from H-118 (platform-vendor arq. L.R., workshop 2026-04-13 W2):
    platform-vendor uses HashiCorp Vault on-premise under the internal
    alias "Bolt". Runtime hash → env var injection, per-app scope,
    manual rotation for DB creds, external users rotated.
    """

    product: str = "env-vars"              # "hashicorp-vault" | "aws-secrets-manager" | "azure-keyvault" | "env-vars" | "config-files"
    internal_alias: str = ""               # "Bolt" for platform-vendor's HashiCorp Vault
    scope: str = "per-app"                 # "per-app" | "shared-vault" | "none"
    rotation_policy: str = "manual"        # "automatic" | "manual" | "none"
    hash_based_injection: bool = False     # True for Vault (runtime hash → env var)
    on_premise: bool = False
    rotates_users: bool = False            # external users rotated (workshop W2)
    rotates_db_creds: bool = False         # DB credentials rotation policy


@dataclass
class ModernizationProgram:
    """An existing institutional modernization program that the tenant
    is already running (or has run).

    Gap D correction (2026-04-12) — AM Dynamics is NOT an ERP. It is
    the client's internal cloud-migration program (~350 apps, 200+
    migrated, 4 R-strategies). Modeling it correctly lets the strangler
    planner align refactor phases with what the institution already did
    (e.g., 3 of the 5 scope apps already passed through Dynamics).
    """

    name: str = ""                         # "dynamics" for tenant-alpha
    total_apps: int = 0                    # 350 for tenant-alpha
    migrated_apps: int = 0                 # 200+ for tenant-alpha (~57%)
    strategies: list[str] = field(default_factory=list)  # ["retire", "refactor", "replatform", "rehost"]
    activities_per_app: int = 0            # 170 for tenant-alpha (Atlas framework)
    tier_classification: dict = field(default_factory=dict)  # {"tier0": "5min downtime", "tier1": ...}
    scope_apps_status: dict = field(default_factory=dict)  # {"app-01": "not-started", "app-03": "completed"}


@dataclass
class ThirdPartyDep:
    """One third-party dependency that is not the main platform vendor.

    Gap K (2026-04-12) — discovery corpus revealed operators and
    contractors (RPA "Doble V", contractor "Multiplica") that touch
    critical processes but are NOT inventoried anywhere. The refactor
    engine should flag undocumented third-party dependencies as risk.
    """

    name: str                              # codename, e.g., "valdemar-rpa"
    role: str = "unknown"                  # "rpa-operator" | "dev-contractor" | "infra-provider"
    documented: bool = False               # False → this dependency has no documentation
    risk_level: str = "medium"             # "low" | "medium" | "high" | "critical"
    apps_affected: list[str] = field(default_factory=list)  # codenames


@dataclass
class NonScopeAppStub:
    """One non-scope application in the tenant ecosystem.

    Phase B scaffolding (2026-04-11) — the 5 full-recipe apps in
    ``TenantProfile.apps`` represent the scope of the modernization
    engagement we have real data for. The remaining ~26 apps in the
    31-app enterprise footprint are **not in current scope** and
    should NOT be generated as fabricated code trees (fake numbers
    would undermine the "weeks not years" narrative credibility).

    Instead, each non-scope app gets a ``DISCOVERY_PENDING.md`` stub
    that records its codename, a short label, a category
    classification, and optional notes. The refactor engine treats
    these as "scope requires discovery" during ingestion so they
    appear in the tenant tree count without polluting the findings
    totals from the 5 scope apps.

    This matches the pattern originally proposed for app-05 in
    ``integration/02_phase2_plan.md`` §3 before that app was
    promoted to a full recipe after the vendor Report Out.
    """

    codename: str  # e.g., "app-06"
    label: str = ""  # short generic label
    category: str = "satellite"  # satellite / shared-library / archival / utility / integration
    notes: str = ""  # free-form notes (kept deliberately short)

    def to_stub_markdown(self) -> str:
        label = self.label or self.codename
        notes = self.notes.strip() or "(no additional notes)"
        return (
            f"# `{self.codename}` — DISCOVERY PENDING\n\n"
            f"**Label:** {label}\n"
            f"**Category:** `{self.category}`\n"
            f"**Action:** `TBD` (requires discovery phase before classification)\n"
            f"**In scope:** NO — non-scope app in the 31-app enterprise footprint\n\n"
            f"## Notes\n\n{notes}\n\n"
            f"## Why this file exists\n\n"
            f"This app is part of the 31-app tenant ecosystem but is **not in the "
            f"current modernization scope**. The synth generator emits this stub so "
            f"that ingestion, dependency mapping and stakeholder tooling correctly "
            f"count the app toward the overall footprint without the refactor engine "
            f"trying to analyze fabricated code.\n\n"
            f"When this app enters scope in a future phase, replace this stub with a "
            f"full recipe entry in ``backend/app/synth/fixtures/tenant_alpha.yaml`` "
            f"under ``apps:`` and remove the corresponding entry from "
            f"``non_scope_apps:``.\n\n"
            f"_Auto-generated by the synth Phase B scaffolding._\n"
        )


@dataclass
class TenantProfile:
    """Top-level tenant configuration."""

    tenant_id: str  # slug, e.g., "tenant-alpha"
    display_name: str  # e.g., "Alpha Corp"
    seed: int = 42
    apps: list[AppRecipe] = field(default_factory=list)
    description: str = ""
    compliance: ComplianceProfile | None = None
    commercial_risk: CommercialRiskProfile | None = None
    governance: GovernanceProfile | None = None
    # Discovery-sourced profiles (Gaps C, D, J, K, P-005 — 2026-04-12)
    platform_vendor: PlatformVendor | None = None
    infrastructure_risk: InfrastructureRisk | None = None
    modernization_program: ModernizationProgram | None = None
    orchestration_model: str = "unknown"  # "none" | "manual" | "semi-auto" | "fully-orchestrated"
    third_party_deps: list[ThirdPartyDep] = field(default_factory=list)
    # P-010 / Gap M (2026-04-13) — secret management posture (Bolt/Vault).
    # Optional: when present, Mythos calibration uses it to avoid flagging
    # env vars injected by Vault as "hardcoded credentials".
    secret_management: SecretManagement | None = None
    # Phase B scaffolding — non-scope apps emitted as discovery-
    # pending stubs only. These count toward ``total_apps`` but NOT
    # toward ``total_loc`` or ``total_vulnerabilities``.
    non_scope_apps: list[NonScopeAppStub] = field(default_factory=list)

    def app_by_codename(self, codename: str) -> AppRecipe | None:
        for app in self.apps:
            if app.codename == codename:
                return app
        return None

    def total_loc(self) -> int:
        return sum(a.loc_target for a in self.apps)

    def total_vulnerabilities(self) -> int:
        return sum(a.vulnerabilities.total() for a in self.apps)

    def total_apps(self) -> int:
        """Total apps in the tenant footprint = scope apps + non-scope
        stubs. Phase A alone returns len(self.apps); with Phase B
        stubs loaded this reaches the 31-app target."""
        return len(self.apps) + len(self.non_scope_apps)


def load_profile(path: str | Path) -> TenantProfile:
    """Load a TenantProfile from a YAML fixture file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Tenant profile fixture not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    apps: list[AppRecipe] = []
    for raw_app in raw.get("apps", []):
        dbs = [
            DatabaseSpec(
                engine=d["engine"],
                tables=d.get("tables", 20),
                pii_columns=d.get("pii_columns", 5),
            )
            for d in raw_app.get("databases", [])
        ]
        vuln_raw = raw_app.get("vulnerabilities", {})
        vulns = VulnerabilityDensity(
            sql_injection=vuln_raw.get("sql_injection", 0),
            hardcoded_creds=vuln_raw.get("hardcoded_creds", 0),
            weak_crypto=vuln_raw.get("weak_crypto", 0),
            command_injection=vuln_raw.get("command_injection", 0),
            missing_fk=vuln_raw.get("missing_fk", 0),
            pii_leak=vuln_raw.get("pii_leak", 0),
            suppressed_exceptions=vuln_raw.get("suppressed_exceptions", 0),
        )
        sub_projects = []
        for sp in raw_app.get("sub_projects", []):
            op_raw = sp.get("operational")
            operational = None
            if op_raw:
                windows = [
                    OperationalWindow(
                        start=str(w.get("start", "")),
                        end=str(w.get("end", "")),
                        region=str(w.get("region", "")),
                    )
                    for w in (op_raw.get("operational_windows") or [])
                    if isinstance(w, dict)
                ]
                operational = OperationalProfile(
                    user_count=int(op_raw.get("user_count", 0) or 0),
                    user_roles=list(op_raw.get("user_roles") or []),
                    daily_request_volume=int(op_raw.get("daily_request_volume", 0) or 0),
                    historical_volume=int(op_raw.get("historical_volume", 0) or 0),
                    operational_windows=windows,
                    vpn_required=bool(op_raw.get("vpn_required", False)),
                    mfa_required=bool(op_raw.get("mfa_required", False)),
                    planned_integrations=list(op_raw.get("planned_integrations") or []),
                )
            sub_projects.append(SubProject(
                name=sp["name"],
                language=sp["language"],
                loc_share=sp.get("loc_share", 1.0),
                vuln_share=sp.get("vuln_share", 1.0),
                modules=sp.get("modules", 6),
                has_rpa=sp.get("has_rpa", False),
                operational=operational,
            ))
        decision_raw = raw_app.get("decision")
        decision = None
        if decision_raw:
            decision = RefactorDecision(
                action=decision_raw.get("action", "refactor"),
                phase=decision_raw.get("phase", "Q3"),
                rationale=decision_raw.get("rationale", ""),
                validation_checklist=decision_raw.get("validation_checklist", []),
                blockers=decision_raw.get("blockers", []),
                gate_type=str(decision_raw.get("gate_type", "")),
                evidence_for=list(decision_raw.get("evidence_for") or []),
                evidence_against=list(decision_raw.get("evidence_against") or []),
                blocker_to_resolve=str(decision_raw.get("blocker_to_resolve", "")),
                estimated_savings_if_taken=str(decision_raw.get("estimated_savings_if_taken", "")),
                stakeholders_to_confirm=list(decision_raw.get("stakeholders_to_confirm") or []),
            )
        mr_raw = raw_app.get("multi_robot")
        multi_robot = None
        if mr_raw:
            multi_robot = MultiRobotPipeline(
                robot_count=int(mr_raw.get("robot_count", 1) or 1),
                coordination=str(mr_raw.get("coordination", "none")),
                stages=list(mr_raw.get("stages") or []),
                compensation_transactions=bool(
                    mr_raw.get("compensation_transactions", False)
                ),
                failure_detection=str(mr_raw.get("failure_detection", "none")),
                scraping_based=bool(mr_raw.get("scraping_based", False)),
                upstream_ui_owner=str(mr_raw.get("upstream_ui_owner", "")),
                broker_location=str(mr_raw.get("broker_location", "")),
                schedule=str(mr_raw.get("schedule", "")),
            )
        exp_raw = raw_app.get("exposure")
        exposure = None
        if exp_raw:
            exposure = ExposureProfile(
                surface=str(exp_raw.get("surface", "internal-only")),
                dual_backend=bool(exp_raw.get("dual_backend", False)),
                auth_layers=list(exp_raw.get("auth_layers") or []),
                edge_protection=str(exp_raw.get("edge_protection", "none")),
                geo_restrictions=list(exp_raw.get("geo_restrictions") or []),
                user_count=int(exp_raw.get("user_count", 0) or 0),
                mfa_required=bool(exp_raw.get("mfa_required", False)),
            )
        regional_policies: list[RegionalPolicy] = []
        for rp_raw in (raw_app.get("regional_policies") or []):
            if not isinstance(rp_raw, dict):
                continue
            regional_policies.append(RegionalPolicy(
                region_scope=str(rp_raw.get("region_scope", "country")),
                regions=list(rp_raw.get("regions") or []),
                policy_type=str(rp_raw.get("policy_type", "")),
                externalization=str(rp_raw.get("externalization", "unknown")),
                owner=str(rp_raw.get("owner", "")),
            ))
        apps.append(
            AppRecipe(
                codename=raw_app["codename"],
                label=raw_app["label"],
                loc_target=raw_app.get("loc_target", 50_000),
                primary_language=raw_app["primary_language"],
                additional_languages=raw_app.get("additional_languages", []),
                databases=dbs,
                vulnerabilities=vulns,
                has_cobol_layer=raw_app.get("has_cobol_layer", False),
                is_shared_nexus=raw_app.get("is_shared_nexus", False),
                has_rpa=raw_app.get("has_rpa", False),
                modules=raw_app.get("modules", 10),
                sub_projects=sub_projects,
                db_inactive_since=raw_app.get("db_inactive_since", ""),
                decision=decision,
                inject_legacy_db_schema=raw_app.get("inject_legacy_db_schema", False),
                inject_god_method_cc=raw_app.get("inject_god_method_cc", 0),
                multi_robot=multi_robot,
                exposure=exposure,
                regional_policies=regional_policies,
            )
        )

    compliance = None
    raw_compliance = raw.get("compliance")
    if raw_compliance:
        compliance = ComplianceProfile(
            hard_deadline=raw_compliance.get("hard_deadline", ""),
            audit_cadence=raw_compliance.get("audit_cadence", ""),
            narrative=raw_compliance.get("narrative", ""),
            certifications=[
                ComplianceCertification(
                    name=c["name"],
                    framework=c.get("framework", ""),
                    due_date=c.get("due_date", ""),
                    status=c.get("status", "in_progress"),
                    owner=c.get("owner", "compliance"),
                    description=c.get("description", ""),
                )
                for c in raw_compliance.get("certifications", [])
            ],
            phases=[
                ModernizationPhase(
                    name=p["name"],
                    start_date=p.get("start_date", ""),
                    end_date=p.get("end_date", ""),
                    milestones=p.get("milestones", []),
                )
                for p in raw_compliance.get("phases", [])
            ],
        )

    commercial_risk = None
    raw_cr = raw.get("commercial_risk")
    if raw_cr:
        raw_lr = raw_cr.get("legal_risk")
        legal_risk = None
        if raw_lr:
            legal_risk = LegalRisk(
                nda_signed_date=str(raw_lr.get("nda_signed_date", "")),
                nda_status=str(raw_lr.get("nda_status", "current")),
                nda_renewal_required=bool(raw_lr.get("nda_renewal_required", False)),
                nda_notes=str(raw_lr.get("nda_notes", "")),
                contract_coverage_pct=float(raw_lr.get("contract_coverage_pct", 100.0) or 100.0),
                uncovered_spend_usd=float(raw_lr.get("uncovered_spend_usd", 0.0) or 0.0),
                paraguas_contract_name=str(raw_lr.get("paraguas_contract_name", "")),
                paraguas_contract_signed_year=int(raw_lr.get("paraguas_contract_signed_year", 0) or 0),
            )
        commercial_risk = CommercialRiskProfile(
            contract_gap_pct=raw_cr.get("contract_gap_pct", 0.0),
            total_exposure_usd=raw_cr.get("total_exposure_usd", 0.0),
            narrative=raw_cr.get("narrative", ""),
            legal_risk=legal_risk,
            vendors=[
                VendorDependency(
                    name=v["name"],
                    category=v.get("category", "saas"),
                    revenue_share_pct=v.get("revenue_share_pct", 0.0),
                    spend_2y_usd=v.get("spend_2y_usd", 0.0),
                    contract_coverage_pct=v.get("contract_coverage_pct", 100.0),
                    lock_in_level=v.get("lock_in_level", "medium"),
                    notes=v.get("notes", ""),
                )
                for v in raw_cr.get("vendors", [])
            ],
            penalty_exposure=[
                PenaltyExposure(
                    category=p["category"],
                    cap_usd=p.get("cap_usd", 0.0),
                    driver=p.get("driver", ""),
                )
                for p in raw_cr.get("penalty_exposure", [])
            ],
        )

    governance = None
    raw_gov = raw.get("governance")
    if raw_gov:
        steering_raw = raw_gov.get("steering")
        steering = (
            SteeringCommittee(
                cadence=steering_raw.get("cadence", ""),
                attendees=steering_raw.get("attendees", []),
                owner_role=steering_raw.get("owner_role", ""),
                first_formal_review=steering_raw.get("first_formal_review", ""),
            )
            if steering_raw
            else None
        )
        code_raw = raw_gov.get("code_access")
        code_access = (
            CodeAccessGate(
                model=code_raw.get("model", "direct"),
                owner_role=code_raw.get("owner_role", ""),
                bottleneck=code_raw.get("bottleneck", False),
                notes=code_raw.get("notes", ""),
            )
            if code_raw
            else None
        )
        lead_raw = raw_gov.get("tech_lead")
        tech_lead = (
            TechLeadRole(
                status=lead_raw.get("status", "unfilled"),
                scope=lead_raw.get("scope", ""),
                target_start_date=lead_raw.get("target_start_date", ""),
            )
            if lead_raw
            else None
        )
        governance = GovernanceProfile(
            steering=steering,
            code_access=code_access,
            tech_lead=tech_lead,
            raci_summary=raw_gov.get("raci_summary", ""),
            narrative=raw_gov.get("narrative", ""),
            teams=[
                GovernanceTeam(
                    name=t["name"],
                    role=t.get("role", "primary-delivery"),
                    app_scope=t.get("app_scope", []),
                    headcount=t.get("headcount", 0),
                    status=t.get("status", "active"),
                )
                for t in raw_gov.get("teams", [])
            ],
        )

    # Phase B scaffolding — parse non-scope stubs, if any.
    non_scope_apps: list[NonScopeAppStub] = []
    for raw_stub in raw.get("non_scope_apps", []) or []:
        # Support both dict form and short-form "just a codename string"
        if isinstance(raw_stub, str):
            non_scope_apps.append(NonScopeAppStub(codename=raw_stub))
            continue
        non_scope_apps.append(
            NonScopeAppStub(
                codename=raw_stub["codename"],
                label=raw_stub.get("label", ""),
                category=raw_stub.get("category", "satellite"),
                notes=raw_stub.get("notes", ""),
            )
        )

    # Discovery-sourced profiles (Gaps C, D, J, K, P-005 — 2026-04-12)
    platform_vendor = None
    raw_pv = raw.get("platform_vendor")
    if raw_pv:
        platform_vendor = PlatformVendor(
            name=raw_pv.get("name", ""),
            surface_area=raw_pv.get("surface_area", []),
            lock_in_level=raw_pv.get("lock_in_level", "high"),
            exit_plan=raw_pv.get("exit_plan", ""),
            dependent_apps=raw_pv.get("dependent_apps", []),
            controls_production=raw_pv.get("controls_production", True),
            controls_credentials=raw_pv.get("controls_credentials", True),
            sla_hours=raw_pv.get("sla_hours", 24),
        )

    infrastructure_risk = None
    raw_ir = raw.get("infrastructure_risk")
    if raw_ir:
        raw_es = raw_ir.get("edge_security")
        edge_security = None
        if raw_es:
            edge_security = EdgeSecurity(
                waf_present=bool(raw_es.get("waf_present", False)),
                waf_provider=str(raw_es.get("waf_provider", "none")),
                geo_blocking=list(raw_es.get("geo_blocking") or []),
                pattern_rules=list(raw_es.get("pattern_rules") or []),
                scan_cadence=str(raw_es.get("scan_cadence", "none")),
                remediation_channel=str(raw_es.get("remediation_channel", "none")),
            )
        infrastructure_risk = InfrastructureRisk(
            orchestrator=raw_ir.get("orchestrator", "none"),
            blueprint_exists=raw_ir.get("blueprint_exists", True),
            server_model=raw_ir.get("server_model", ""),
            server_count=raw_ir.get("server_count", 1),
            environments_on_same_server=raw_ir.get("environments_on_same_server", False),
            redundancy_type=raw_ir.get("redundancy_type", "none"),
            capacity_planning_freq=raw_ir.get("capacity_planning_freq", "annual"),
            edge_security=edge_security,
        )

    secret_management = None
    raw_sm = raw.get("secret_management")
    if raw_sm:
        secret_management = SecretManagement(
            product=str(raw_sm.get("product", "env-vars")),
            internal_alias=str(raw_sm.get("internal_alias", "")),
            scope=str(raw_sm.get("scope", "per-app")),
            rotation_policy=str(raw_sm.get("rotation_policy", "manual")),
            hash_based_injection=bool(raw_sm.get("hash_based_injection", False)),
            on_premise=bool(raw_sm.get("on_premise", False)),
            rotates_users=bool(raw_sm.get("rotates_users", False)),
            rotates_db_creds=bool(raw_sm.get("rotates_db_creds", False)),
        )

    modernization_program = None
    raw_mp = raw.get("modernization_program")
    if raw_mp:
        modernization_program = ModernizationProgram(
            name=raw_mp.get("name", ""),
            total_apps=raw_mp.get("total_apps", 0),
            migrated_apps=raw_mp.get("migrated_apps", 0),
            strategies=raw_mp.get("strategies", []),
            activities_per_app=raw_mp.get("activities_per_app", 0),
            tier_classification=raw_mp.get("tier_classification", {}),
            scope_apps_status=raw_mp.get("scope_apps_status", {}),
        )

    third_party_deps: list[ThirdPartyDep] = []
    for raw_tp in raw.get("third_party_deps", []) or []:
        third_party_deps.append(
            ThirdPartyDep(
                name=raw_tp["name"],
                role=raw_tp.get("role", "unknown"),
                documented=raw_tp.get("documented", False),
                risk_level=raw_tp.get("risk_level", "medium"),
                apps_affected=raw_tp.get("apps_affected", []),
            )
        )

    return TenantProfile(
        tenant_id=raw["tenant_id"],
        display_name=raw["display_name"],
        seed=raw.get("seed", 42),
        description=raw.get("description", ""),
        apps=apps,
        compliance=compliance,
        commercial_risk=commercial_risk,
        governance=governance,
        platform_vendor=platform_vendor,
        infrastructure_risk=infrastructure_risk,
        modernization_program=modernization_program,
        orchestration_model=raw.get("orchestration_model", "unknown"),
        third_party_deps=third_party_deps,
        secret_management=secret_management,
        non_scope_apps=non_scope_apps,
    )
