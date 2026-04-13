"""Strangler-pattern migration planner — Phase 4 Gap 3.

Takes a ``ProjectGraph`` from the ingestion engine and produces a phased
decomposition plan that walks a legacy monolith-nexus through the
strangler-fig pattern: outer layers extracted first, domain core last,
mainframe components wrapped (never rewritten).

The planner uses a hybrid approach:
- Architectural heuristics over the module directory structure
  (controllers, repositories, models, shared libraries, mainframe code)
- Finding density (from the ingestion engine's vulnerability hotspots)
  to weight risk per phase
- Coupling signals (depends_on / depended_by from ProjectGraph.modules)
  when available

Output: a ``StranglerPlan`` containing ordered ``StranglerPhase`` items
with rationale, risk, effort estimate, rollback strategy and a narrative
paragraph. Also renders a Markdown plan for stakeholder review.

Designed for enterprise legacy nexus systems: a single application that
owns the revenue model and ties dozens of satellite apps together. The
planner produces a multi-month roadmap that lets the client prove value
incrementally instead of attempting a big-bang rewrite.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .ingestion import ProjectGraph, RepoIngestionEngine

logger = logging.getLogger(__name__)

# Lazy import to avoid circular deps — discovery_loader is optional.
# When not available, the planner works exactly as before (code-only).
DiscoveryIndex = None  # type: Any
try:
    from .discovery_loader import DiscoveryIndex as _DI
    DiscoveryIndex = _DI
except ImportError:
    pass


# ── Role classification heuristics ─────────────────────────────────────────


_ROLE_HINTS: list[tuple[str, str]] = [
    ("controllers", "controller"),
    ("controller", "controller"),
    ("api/", "controller"),
    ("apis/", "controller"),
    ("routes/", "controller"),
    ("endpoints/", "controller"),
    ("repositories", "repository"),
    ("repository", "repository"),
    ("dal/", "repository"),
    ("dao/", "repository"),
    ("data/", "repository"),
    ("models", "model"),
    ("model/", "model"),
    ("entities", "model"),
    ("domain/", "model"),
    ("services", "service"),
    ("service/", "service"),
    ("business/", "service"),
    ("shared", "shared"),
    ("common", "shared"),
    ("core", "shared"),
    ("util", "shared"),
    ("infra", "shared"),
    ("cobol", "mainframe"),
    ("vsam", "mainframe"),
    ("jcl", "mainframe"),
    ("copybook", "mainframe"),
]


def classify_module(module_name: str, module_path: str) -> str:
    """Classify a module into a strangler role based on its path / name.

    Roles (ordered from lowest to highest extraction risk):
      - controller   — outer HTTP layer, easy to wrap behind a gateway
      - model        — domain entities, extract with owning service
      - service      — business logic, medium risk
      - repository   — data access, requires schema coordination
      - shared       — cross-cutting legacy libraries, high risk
      - mainframe    — COBOL / VSAM, strangler-wrap only (never rewrite)
      - unknown      — treat as shared (conservative)
    """
    needle = f"{module_name}/{module_path}".lower()
    for hint, role in _ROLE_HINTS:
        if hint in needle:
            return role
    return "unknown"


# Extraction order — lower number extracted earlier
_ROLE_ORDER: dict[str, int] = {
    "controller": 1,
    "model": 2,
    "service": 3,
    "repository": 4,
    "unknown": 5,
    "shared": 6,
    "mainframe": 7,
}


_ROLE_DEFAULT_STRATEGY: dict[str, str] = {
    "controller": (
        "Place API Gateway in front. Route new requests to extracted "
        "microservice; legacy endpoints stay live until traffic shifts."
    ),
    "model": (
        "Extract domain entities into a shared contracts package "
        "consumed by both the legacy app and the new service."
    ),
    "service": (
        "Run new service alongside legacy. Use dual-write or event "
        "sourcing to keep state consistent during cut-over."
    ),
    "repository": (
        "Introduce an anti-corruption layer over the legacy DB. New "
        "service reads via views; writes flow through the legacy path "
        "until the schema is owned by the new service."
    ),
    "shared": (
        "Identify consumers and lift the shared module into a versioned "
        "package. Extract one consumer at a time; deprecate the shared "
        "copy once all consumers migrate."
    ),
    "mainframe": (
        "DO NOT rewrite. Wrap mainframe programs with a thin API "
        "adapter (REST or message queue) so new services consume them "
        "as dependencies. Plan replacement only after all callers migrate."
    ),
    "unknown": (
        "Audit the module before extraction. If it matches the shared "
        "library pattern, treat it as high risk and handle it near the "
        "end of the plan."
    ),
}


# ── Plan dataclasses ───────────────────────────────────────────────────────


@dataclass
class PhaseModule:
    name: str
    role: str
    path: str
    lines_of_code: int
    vulnerability_count: int
    depended_by_count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StranglerPhase:
    index: int
    title: str
    role: str
    modules: list[PhaseModule] = field(default_factory=list)
    strategy: str = ""
    risk: str = "medium"           # low / medium / high
    effort_days: int = 0
    rollback: str = ""
    rationale: str = ""

    @property
    def total_loc(self) -> int:
        return sum(m.lines_of_code for m in self.modules)

    @property
    def total_vulns(self) -> int:
        return sum(m.vulnerability_count for m in self.modules)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "role": self.role,
            "modules": [m.to_dict() for m in self.modules],
            "strategy": self.strategy,
            "risk": self.risk,
            "effort_days": self.effort_days,
            "rollback": self.rollback,
            "rationale": self.rationale,
            "total_loc": self.total_loc,
            "total_vulns": self.total_vulns,
        }


@dataclass
class PreAssignedDecision:
    """Refactor decision read from a ``refactor_decision.md`` file.

    When the synth generator emits this file for an app (Batch 3+), the
    planner honors the pre-assigned action and phase instead of running
    its default role-based decomposition. This lets the Plan Componer
    Deuda pattern override the generic planner — e.g., an app can be
    marked ``RETIRE`` with dual-validation blockers, and the planner
    will produce a retirement plan rather than a refactor plan.
    """

    action: str = "refactor"  # refactor / retire / retain / tbd
    phase: str = "Q3"
    rationale: str = ""
    validation_checklist: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    # P-018 / Gap T (2026-04-13) — decision gate mirror of
    # RefactorDecision. Parsed from the markdown if present; empty
    # otherwise. Used by render_markdown to surface a "Decision Gate"
    # section so stakeholders see pending calls explicitly.
    gate_type: str = ""
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    blocker_to_resolve: str = ""
    estimated_savings_if_taken: str = ""
    stakeholders_to_confirm: list[str] = field(default_factory=list)

    @property
    def is_gate(self) -> bool:
        return bool(self.gate_type) or self.action.lower() in ("tbd", "gate")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StranglerPlan:
    app_name: str
    app_path: str
    total_modules: int = 0
    total_loc: int = 0
    total_vulns: int = 0
    phases: list[StranglerPhase] = field(default_factory=list)
    narrative: str = ""
    pre_assigned_decision: PreAssignedDecision | None = None
    db_inactive_since: str = ""  # ISO date if the app has an inactive DB marker
    # Discovery context (Gap F wire-up, 2026-04-12). When the planner
    # is given a DiscoveryIndex, it enriches the plan with findings
    # from the corpus: blockers, quick wins, corrections, risk boosts.
    # The discovery_summary is a human-readable digest appended to the
    # narrative; discovery_findings_count tracks how many findings
    # were relevant to this app.
    discovery_findings_count: int = 0
    discovery_blockers: list[str] = field(default_factory=list)
    discovery_quick_wins: list[str] = field(default_factory=list)
    discovery_corrections: list[str] = field(default_factory=list)

    # Ecosystem prior (P-021 wire-up, 2026-04-13). When the planner is
    # given an EcosystemMetrics instance, it surfaces the app's priority
    # score + rationale + critical density so the order of execution
    # honors the ecosystem-wide ranking instead of treating this app
    # in isolation.
    ecosystem_priority_score: float = 0.0
    ecosystem_priority_rationale: str = ""
    ecosystem_critical_density_pct: float = 0.0
    ecosystem_blocker_count: int = 0
    ecosystem_hosting: str = ""
    ecosystem_risk_total_usd: float = 0.0

    # Recipe-level priors from the tenant profile (2026-04-13 EVE):
    # MultiRobotPipeline.risk_level + recommendations, OperationalProfile
    # windows, RegionalPolicy externalization flags. These let the plan
    # reflect architectural constraints that the graph analysis alone
    # cannot detect (e.g., 3 robots + ZMQ without compensation = HIGH
    # risk regardless of LOC or findings).
    multi_robot_risk: str = ""                # "" | "low" | "medium" | "high"
    multi_robot_recommendations: list[str] = field(default_factory=list)
    operational_windows_summary: str = ""     # human-readable, e.g. "81 users, 4 windows 08-20 MX"
    regional_policy_warnings: list[str] = field(default_factory=list)

    @property
    def total_effort_days(self) -> int:
        return sum(p.effort_days for p in self.phases)

    def to_dict(self) -> dict:
        return {
            "app_name": self.app_name,
            "app_path": self.app_path,
            "total_modules": self.total_modules,
            "total_loc": self.total_loc,
            "total_vulns": self.total_vulns,
            "total_effort_days": self.total_effort_days,
            "phases": [p.to_dict() for p in self.phases],
            "narrative": self.narrative,
            "pre_assigned_decision": (
                self.pre_assigned_decision.to_dict()
                if self.pre_assigned_decision
                else None
            ),
            "db_inactive_since": self.db_inactive_since,
            "discovery_findings_count": self.discovery_findings_count,
            "discovery_blockers": self.discovery_blockers,
            "discovery_quick_wins": self.discovery_quick_wins,
            "discovery_corrections": self.discovery_corrections,
            "ecosystem_priority_score": self.ecosystem_priority_score,
            "ecosystem_priority_rationale": self.ecosystem_priority_rationale,
            "ecosystem_critical_density_pct": self.ecosystem_critical_density_pct,
            "ecosystem_blocker_count": self.ecosystem_blocker_count,
            "ecosystem_hosting": self.ecosystem_hosting,
            "ecosystem_risk_total_usd": self.ecosystem_risk_total_usd,
            "multi_robot_risk": self.multi_robot_risk,
            "multi_robot_recommendations": self.multi_robot_recommendations,
            "operational_windows_summary": self.operational_windows_summary,
            "regional_policy_warnings": self.regional_policy_warnings,
        }


# ── refactor_decision.md parser ────────────────────────────────────────────


_DECISION_ACTION_RE = re.compile(r"\*\*Action:\*\*\s*`([A-Z]+)`", re.IGNORECASE)
_DECISION_PHASE_RE = re.compile(r"\*\*Phase:\*\*\s*([^\n]+)")


def _read_pre_assigned_decision(app_dir: Path) -> PreAssignedDecision | None:
    """Parse an optional ``refactor_decision.md`` at the app root.

    The file format is the one produced by
    ``app.synth.profile.RefactorDecision.to_markdown``: markdown with an
    Action line, a Phase line, a Rationale section, a Validation checklist
    section and a Blockers section. We parse just enough to recover the
    structured fields — anything we cannot parse is left at defaults.
    """
    path = app_dir / "refactor_decision.md"
    if not path.exists():
        return None

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return None

    decision = PreAssignedDecision()

    m = _DECISION_ACTION_RE.search(text)
    if m:
        decision.action = m.group(1).strip().lower()
    m = _DECISION_PHASE_RE.search(text)
    if m:
        decision.phase = m.group(1).strip()

    # Extract rationale section
    rationale_match = re.search(
        r"##\s*Rationale\s*\n\s*(.+?)(?:\n##|\Z)", text, re.DOTALL
    )
    if rationale_match:
        decision.rationale = rationale_match.group(1).strip()

    # Extract checklist (lines starting with "- [ ]" or "- [x]")
    checklist: list[str] = []
    in_checklist = False
    for line in text.splitlines():
        if line.startswith("## Validation checklist"):
            in_checklist = True
            continue
        if in_checklist:
            if line.startswith("## "):
                break
            stripped = line.strip()
            if stripped.startswith(("- [ ]", "- [x]", "- [X]")):
                checklist.append(stripped[5:].strip())
    decision.validation_checklist = checklist

    # Extract blockers
    blockers: list[str] = []
    in_blockers = False
    for line in text.splitlines():
        if line.startswith("## Blockers"):
            in_blockers = True
            continue
        if in_blockers:
            if line.startswith("## "):
                break
            stripped = line.strip()
            if stripped.startswith("- ") and stripped != "- (none)":
                blockers.append(stripped[2:].strip())
    decision.blockers = blockers

    # P-018 — parse optional decision gate section
    gate_match = re.search(
        r"##\s*Decision gate\s*—\s*`([^`]+)`", text, re.IGNORECASE
    )
    if gate_match:
        decision.gate_type = gate_match.group(1).strip()

        def _bulleted_section(header_re: str) -> list[str]:
            """Capture bullet points that follow a bolded sub-header."""
            items: list[str] = []
            in_section = False
            for line in text.splitlines():
                if re.search(header_re, line, re.IGNORECASE):
                    in_section = True
                    continue
                if in_section:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped.startswith("- ") and stripped != "- (none)":
                        items.append(stripped[2:].strip())
                    elif stripped.startswith("**") or stripped.startswith("## "):
                        break
            return items

        decision.evidence_for = _bulleted_section(r"\*\*Evidence FOR")
        decision.evidence_against = _bulleted_section(r"\*\*Evidence AGAINST")

        btr_match = re.search(
            r"\*\*Blocker to resolve:\*\*\s*([^\n]+)", text
        )
        if btr_match:
            decision.blocker_to_resolve = btr_match.group(1).strip()

        saving_match = re.search(
            r"\*\*Estimated savings if taken:\*\*\s*([^\n]+)", text
        )
        if saving_match:
            decision.estimated_savings_if_taken = saving_match.group(1).strip()

        stake_match = re.search(
            r"\*\*Stakeholders to confirm:\*\*\s*([^\n]+)", text
        )
        if stake_match:
            raw_stakes = stake_match.group(1).strip()
            if raw_stakes and raw_stakes != "(not specified)":
                decision.stakeholders_to_confirm = [
                    s.strip() for s in raw_stakes.split(",") if s.strip()
                ]

    return decision


def _read_db_inactive_marker(app_dir: Path) -> str:
    """Read a ``db_inactive_since.txt`` marker and return the ISO date.

    The file may contain additional human-readable comment lines prefixed
    with ``#``; we only care about the first non-comment line.
    """
    marker = app_dir / "db_inactive_since.txt"
    if not marker.exists():
        return ""
    try:
        for raw in marker.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                return line
    except OSError as exc:
        logger.warning("Failed to read %s: %s", marker, exc)
    return ""


# ── Planner ────────────────────────────────────────────────────────────────


def _risk_for_role(role: str, total_loc: int, total_vulns: int, depended_by: int) -> str:
    if role == "mainframe":
        return "high"
    if role == "shared":
        return "high"
    if role in {"controller", "model"} and depended_by < 3:
        return "low"
    if total_vulns > 500 or total_loc > 20_000:
        return "high"
    if total_vulns > 100 or total_loc > 5_000:
        return "medium"
    return "low"


def _effort_days(total_loc: int, total_vulns: int) -> int:
    """Very rough heuristic: ~500 LOC/day + 0.1 day per known finding."""
    loc_days = max(1, total_loc // 500)
    vuln_days = max(0, total_vulns // 10)
    return loc_days + vuln_days


def _build_narrative(plan: StranglerPlan) -> str:
    if not plan.phases:
        return "No modules detected — nothing to plan."

    roles_covered = ", ".join(sorted({p.role for p in plan.phases}))
    return (
        f"The {plan.app_name} application contains {plan.total_modules} modules "
        f"({plan.total_loc:,} lines of code, {plan.total_vulns:,} known "
        f"vulnerabilities). NexusForge proposes a {len(plan.phases)}-phase "
        f"strangler decomposition covering {roles_covered}. Total estimated "
        f"effort: {plan.total_effort_days} engineer-days (~"
        f"{plan.total_effort_days // 5} working weeks for a single engineer, "
        f"or ~{max(1, plan.total_effort_days // 20)} weeks for a 4-engineer "
        f"team working in parallel). Each phase is independently deployable "
        f"and reversible — no big-bang cut-over."
    )


def _build_narrative_with_decision(
    plan: StranglerPlan,
    decision: PreAssignedDecision | None,
) -> str:
    """Like ``_build_narrative`` but prepends a pre-assigned-decision note."""
    base = _build_narrative(plan)
    if decision is None:
        return base
    action = decision.action.upper()
    prefix = (
        f"**Pre-assigned decision: {action}** "
        f"(phase {decision.phase}). "
    )
    if decision.rationale:
        # Collapse whitespace in rationale so it fits the narrative paragraph
        rationale = " ".join(decision.rationale.split())
        prefix += f"Rationale: {rationale} "
    return prefix + base


class StranglerPlanner:
    """Produces a strangler-pattern migration plan for a single app.

    When initialized with a ``discovery_index``, the planner enriches
    its output with findings from the corpus analysis pipeline:

    - Blockers are surfaced as plan-level warnings
    - Quick wins are annotated on the plan for prioritization
    - Corrections override or amend the code-only analysis
    - Risk scores are boosted when discovery blockers are present
    - The narrative includes a discovery context section

    Without a discovery index, the planner works identically to its
    pre-Gap-F behavior (code-only, deterministic).
    """

    def __init__(
        self,
        graph: ProjectGraph,
        discovery_index=None,
        ecosystem_metrics=None,
        app_recipe=None,
    ):
        self.graph = graph
        self._discovery = discovery_index    # DiscoveryIndex | None
        self._ecosystem = ecosystem_metrics  # EcosystemMetrics | None
        self._recipe = app_recipe            # AppRecipe | None — tenant-alpha-style recipe with multi_robot / operational / regional_policies

    def plan(self) -> StranglerPlan:
        plan = StranglerPlan(
            app_name=self.graph.name or Path(self.graph.root).name,
            app_path=self.graph.root,
            total_modules=len(self.graph.modules),
            total_loc=self.graph.total_lines,
        )

        # Aggregate vulnerability totals
        plan.total_vulns = sum(
            m.vulnerability_count for m in self.graph.modules.values()
        )

        # Read pre-assigned decision + db-inactive marker if present
        app_dir = Path(self.graph.root)
        plan.pre_assigned_decision = _read_pre_assigned_decision(app_dir)
        plan.db_inactive_since = _read_db_inactive_marker(app_dir)

        # Short-circuit on non-refactor decisions
        decision = plan.pre_assigned_decision
        if decision is not None and decision.action != "refactor":
            self._apply_non_refactor_decision(plan, decision)
            plan.narrative = _build_narrative_with_decision(plan, decision)
            self._apply_discovery_context(plan)
            return plan

        # Default refactor path — group modules by role
        self._build_refactor_phases(plan)
        plan.narrative = _build_narrative_with_decision(plan, decision)

        # Enrich with discovery context (if available)
        self._apply_discovery_context(plan)

        # P-021 — enrich with ecosystem metrics prior (if available)
        self._apply_ecosystem_metrics(plan)

        # P-012/P-014/P-019 — enrich with recipe priors (multi_robot,
        # operational, regional_policies) when an AppRecipe was supplied.
        self._apply_recipe_priors(plan)
        return plan

    def _apply_recipe_priors(self, plan: StranglerPlan) -> None:
        """Surface multi-robot / operational / regional signals from the recipe.

        No-op when no recipe was attached. Idempotent — re-running does not
        duplicate narrative entries (we check for section headers).
        """
        recipe = self._recipe
        if recipe is None:
            return

        narrative_lines: list[str] = []

        # --- MultiRobotPipeline (P-019) ---
        mr = getattr(recipe, "multi_robot", None)
        if mr is not None:
            risk = mr.risk_level()
            recs = mr.recommendations()
            plan.multi_robot_risk = risk
            plan.multi_robot_recommendations = recs

            # Risk-boost phase 1 when multi-robot risk is high (regardless
            # of LOC/findings — architectural hazard in itself).
            if risk == "high" and plan.phases:
                first = plan.phases[0]
                if first.risk != "high":
                    first.risk = "high"
                    first.rationale += (
                        f" [RISK BOOSTED by multi-robot profile: "
                        f"{mr.robot_count} robots via {mr.coordination}, "
                        f"compensation_transactions={mr.compensation_transactions}]"
                    )
                else:
                    first.rationale += (
                        f" [Multi-robot profile confirms HIGH risk: "
                        f"{mr.robot_count} robots via {mr.coordination}]"
                    )

            narrative_lines.append(f"\n\n## Multi-robot profile (P-019)\n")
            narrative_lines.append(
                f"- **Topology**: {mr.robot_count} robots via "
                f"`{mr.coordination}` broker"
            )
            if mr.stages:
                narrative_lines.append(
                    f"- **Stages**: {' → '.join(mr.stages)}"
                )
            if mr.scraping_based and mr.upstream_ui_owner:
                narrative_lines.append(
                    f"- **Scraping-based**: yes (upstream UI owner: "
                    f"`{mr.upstream_ui_owner}`)"
                )
            narrative_lines.append(f"- **Architectural risk**: **{risk}**")
            if recs:
                narrative_lines.append("- **Refactor recommendations**:")
                for r in recs:
                    narrative_lines.append(f"  - {r}")

        # --- OperationalProfile on sub-projects (P-012) ---
        operational_hits: list[str] = []
        for sub in getattr(recipe, "sub_projects", []) or []:
            op = getattr(sub, "operational", None)
            if op is None:
                continue
            parts: list[str] = []
            if op.user_count:
                parts.append(f"{op.user_count} users")
            if op.daily_request_volume:
                parts.append(f"~{op.daily_request_volume}/day")
            if op.operational_windows:
                firsts = [w.start for w in op.operational_windows if w.start]
                lasts = [w.end for w in op.operational_windows if w.end]
                if firsts and lasts:
                    regions = {w.region for w in op.operational_windows if w.region}
                    region_tag = f" {','.join(sorted(regions))}" if regions else ""
                    parts.append(
                        f"{len(op.operational_windows)} windows "
                        f"{min(firsts)}-{max(lasts)}{region_tag}"
                    )
            if op.vpn_required:
                parts.append("VPN")
            if op.mfa_required:
                parts.append("MFA")
            if parts:
                operational_hits.append(f"{sub.name}: {', '.join(parts)}")

        if operational_hits:
            plan.operational_windows_summary = " | ".join(operational_hits)
            narrative_lines.append("\n\n## Operational profile (P-012)\n")
            for hit in operational_hits:
                narrative_lines.append(f"- {hit}")
            narrative_lines.append(
                "- **Scheduling guidance**: avoid deployment / refactor "
                "windows during active hours listed above."
            )

        # --- RegionalPolicy (P-014) ---
        warnings: list[str] = []
        for rp in getattr(recipe, "regional_policies", []) or []:
            rec_text = rp.refactor_recommendation()
            label = (
                f"{rp.policy_type or 'policy'} "
                f"({rp.region_scope}: {', '.join(rp.regions) or '—'}, "
                f"{rp.externalization})"
            )
            warnings.append(f"{label} — {rec_text}")
        if warnings:
            plan.regional_policy_warnings = warnings
            narrative_lines.append("\n\n## Regional policies (P-014)\n")
            for w in warnings:
                narrative_lines.append(f"- {w}")

        if narrative_lines:
            # Guard against duplication on repeated calls
            if "## Multi-robot profile" not in plan.narrative and \
               "## Operational profile" not in plan.narrative and \
               "## Regional policies" not in plan.narrative:
                plan.narrative += "\n".join(narrative_lines)

    def _apply_ecosystem_metrics(self, plan: StranglerPlan) -> None:
        """Attach ecosystem priority hints + density signals to the plan.

        No-op when no EcosystemMetrics was provided — pre-P-021 behavior
        is preserved byte-for-byte.
        """
        if self._ecosystem is None or not getattr(self._ecosystem, "is_loaded", lambda: False)():
            return

        # Find the codename to query the metrics. Reuse the same
        # fuzzy-match logic as discovery so the two priors align on
        # which codename they attach to.
        app_name = plan.app_name.lower().strip()
        codename = None
        for candidate_app in self._ecosystem.per_app:
            cand = candidate_app.app.lower()
            if cand in app_name or app_name in cand:
                codename = candidate_app.app
                break
        if codename is None:
            path_stem = Path(plan.app_path).name.lower()
            for candidate_app in self._ecosystem.per_app:
                if candidate_app.app.lower() in path_stem:
                    codename = candidate_app.app
                    break
        if codename is None:
            logger.debug(
                "Ecosystem: no matching codename for app '%s'", plan.app_name
            )
            return

        density = self._ecosystem.app(codename)
        hint = self._ecosystem.priority_hint(codename)

        if density is not None:
            plan.ecosystem_critical_density_pct = density.critical_density_pct
            plan.ecosystem_blocker_count = density.blocker_issues
            plan.ecosystem_hosting = density.hosting
        if hint is not None:
            plan.ecosystem_priority_score = hint.priority_score
            plan.ecosystem_priority_rationale = hint.rationale
        plan.ecosystem_risk_total_usd = self._ecosystem.risk_total_usd

        # Narrative enrichment — place the section after discovery context
        summary_lines = ["\n\n## Ecosystem prior (P-021)\n"]
        if hint is not None:
            summary_lines.append(
                f"- **Priority score**: {hint.priority_score:.1f}"
            )
            summary_lines.append(f"- **Rationale**: {hint.rationale}")
        if density is not None:
            summary_lines.append(
                f"- **Critical density**: {density.critical_density_pct:.1f}% "
                f"({density.critical_issues} of {density.total_issues} total)"
            )
            if density.blocker_issues:
                summary_lines.append(f"- **Blocker count**: {density.blocker_issues}")
            if density.hosting:
                summary_lines.append(f"- **Hosting**: {density.hosting}")
        if self._ecosystem.risk_total_usd:
            summary_lines.append(
                f"- **Ecosystem risk exposure**: "
                f"${self._ecosystem.risk_total_usd:,.0f} USD total"
            )
        plan.narrative += "\n".join(summary_lines)

    def _apply_discovery_context(self, plan: StranglerPlan) -> None:
        """Enrich the plan with findings from the corpus pipeline.

        This method is a no-op when no discovery index was provided,
        preserving the pre-Gap-F behavior byte-for-byte.
        """
        if self._discovery is None:
            return

        # Try to match the app name to a codename. The graph name may
        # be "app-01", "sicofav", "Transaction Reconciliation Service",
        # or a filesystem path. We do a fuzzy match against all app
        # codenames mentioned in the discovery index.
        app_name = plan.app_name.lower().strip()
        codename = None
        for candidate in self._discovery.apps_mentioned:
            if candidate.lower() in app_name or app_name in candidate.lower():
                codename = candidate
                break
        # Also try matching by the last directory component of app_path
        if codename is None:
            path_stem = Path(plan.app_path).name.lower()
            for candidate in self._discovery.apps_mentioned:
                if candidate.lower() in path_stem:
                    codename = candidate
                    break

        if codename is None:
            logger.debug(
                "Discovery: no matching codename for app '%s'", plan.app_name
            )
            return

        # Gather findings for this app
        app_findings = self._discovery.findings_for_app(codename)
        if not app_findings:
            return

        plan.discovery_findings_count = len(app_findings)

        # Classify
        for f in app_findings:
            label = f"{f.id}: {f.title}"
            if f.is_blocker:
                plan.discovery_blockers.append(label)
            if f.is_quick_win:
                plan.discovery_quick_wins.append(label)
            if f.is_correction:
                plan.discovery_corrections.append(label)

        # Risk boost: if there are discovery blockers, boost the risk
        # of the highest-risk phase by one level
        if plan.discovery_blockers and plan.phases:
            for phase in plan.phases:
                if phase.risk == "medium":
                    phase.risk = "high"
                    phase.rationale += (
                        f" [RISK BOOSTED by {len(plan.discovery_blockers)} "
                        f"discovery blocker(s)]"
                    )
                    break  # only boost one phase
                elif phase.risk == "high":
                    # Already high — add annotation only
                    phase.rationale += (
                        f" [Discovery confirms {len(plan.discovery_blockers)} "
                        f"blocker(s)]"
                    )
                    break

        # Narrative enrichment
        discovery_lines: list[str] = []
        discovery_lines.append(
            f"\n\n## Discovery context ({plan.discovery_findings_count} "
            f"findings from corpus)\n"
        )
        if plan.discovery_blockers:
            discovery_lines.append(f"\n**Blockers ({len(plan.discovery_blockers)}):**")
            for b in plan.discovery_blockers:
                discovery_lines.append(f"- {b}")
        if plan.discovery_quick_wins:
            discovery_lines.append(
                f"\n**Quick wins ({len(plan.discovery_quick_wins)}):**"
            )
            for q in plan.discovery_quick_wins:
                discovery_lines.append(f"- {q}")
        if plan.discovery_corrections:
            discovery_lines.append(
                f"\n**Model corrections ({len(plan.discovery_corrections)}):**"
            )
            for c in plan.discovery_corrections:
                discovery_lines.append(f"- {c}")

        plan.narrative += "\n".join(discovery_lines)

    def _build_refactor_phases(self, plan: StranglerPlan) -> None:
        by_role: dict[str, list[PhaseModule]] = {}
        for name, module in self.graph.modules.items():
            if name == "_root":
                if len(self.graph.modules) > 1:
                    continue
            role = classify_module(name, module.path)
            pm = PhaseModule(
                name=name,
                role=role,
                path=module.path,
                lines_of_code=module.total_lines,
                vulnerability_count=module.vulnerability_count,
                depended_by_count=len(module.depended_by),
            )
            by_role.setdefault(role, []).append(pm)

        phase_idx = 0
        for role in sorted(by_role, key=lambda r: _ROLE_ORDER.get(r, 99)):
            modules = sorted(by_role[role], key=lambda m: -m.lines_of_code)
            phase_idx += 1

            total_loc = sum(m.lines_of_code for m in modules)
            total_vulns = sum(m.vulnerability_count for m in modules)
            max_depended = max((m.depended_by_count for m in modules), default=0)

            phase = StranglerPhase(
                index=phase_idx,
                title=_phase_title(phase_idx, role, len(modules)),
                role=role,
                modules=modules,
                strategy=_ROLE_DEFAULT_STRATEGY.get(role, _ROLE_DEFAULT_STRATEGY["unknown"]),
                risk=_risk_for_role(role, total_loc, total_vulns, max_depended),
                effort_days=_effort_days(total_loc, total_vulns),
                rollback=_rollback_for_role(role),
                rationale=_rationale_for_role(role, len(modules), total_loc, total_vulns),
            )
            plan.phases.append(phase)

    def _apply_non_refactor_decision(
        self, plan: StranglerPlan, decision: PreAssignedDecision
    ) -> None:
        """Generate a special plan for retire / retain / tbd actions."""
        action = decision.action.lower()
        all_modules = [
            PhaseModule(
                name=name,
                role=classify_module(name, m.path),
                path=m.path,
                lines_of_code=m.total_lines,
                vulnerability_count=m.vulnerability_count,
                depended_by_count=len(m.depended_by),
            )
            for name, m in self.graph.modules.items()
            if name != "_root" or len(self.graph.modules) == 1
        ]

        if action == "retire":
            checklist_text = (
                "\n".join(f"- {item}" for item in decision.validation_checklist)
                or "- (no checklist provided)"
            )
            blockers_text = (
                "\n".join(f"- {item}" for item in decision.blockers)
                or "- (no blockers listed)"
            )
            phase = StranglerPhase(
                index=1,
                title="Phase 1: Decommission with dual validation",
                role="retirement",
                modules=all_modules,
                strategy=(
                    "This app is marked for retirement. Before decommission, "
                    "validate BOTH (1) that remaining exploits are not actually "
                    "reachable, and (2) that no downstream business process "
                    "still depends on the app. If either check fails, reclassify "
                    "as refactor.\n\nValidation checklist:\n" + checklist_text
                    + "\n\nKnown blockers:\n" + blockers_text
                ),
                risk="high",
                effort_days=max(10, len(all_modules) * 3),
                rollback=(
                    "Halt decommission, restore traffic routing to the legacy "
                    "app, and reopen the ticket as a refactor candidate."
                ),
                rationale=decision.rationale or "Pre-assigned retirement decision.",
            )
            plan.phases.append(phase)
            if plan.db_inactive_since:
                phase.rationale += (
                    f"\n\nDatabase has been inactive since {plan.db_inactive_since}, "
                    "which is the primary signal driving the retirement recommendation."
                )

        elif action == "retain":
            phase = StranglerPhase(
                index=1,
                title="Phase 1: Retain as-is with monitoring",
                role="retention",
                modules=all_modules,
                strategy=(
                    "This app is marked for retention. No refactor work is "
                    "planned. Add monitoring, incident runbooks and a formal "
                    "end-of-life review date."
                ),
                risk="low",
                effort_days=max(3, len(all_modules)),
                rollback="N/A — retention decision has no destructive steps.",
                rationale=decision.rationale or "Pre-assigned retention decision.",
            )
            plan.phases.append(phase)

        elif action == "tbd":
            blockers_text = (
                "\n".join(f"- {item}" for item in decision.blockers)
                or "- (no blockers listed)"
            )
            checklist_text = (
                "\n".join(f"- {item}" for item in decision.validation_checklist)
                or "- (no checklist provided)"
            )
            phase = StranglerPhase(
                index=1,
                title="Phase 1: Discovery",
                role="discovery",
                modules=all_modules,
                strategy=(
                    "This app has not been assessed yet. A discovery phase is "
                    "required to build a baseline before the refactor plan "
                    "can be written.\n\nDiscovery checklist:\n" + checklist_text
                    + "\n\nKnown blockers:\n" + blockers_text
                ),
                risk="medium",
                effort_days=max(5, len(all_modules) * 2),
                rollback=(
                    "Discovery phases are non-destructive. If scope changes "
                    "during discovery, update the decision file and re-run "
                    "the planner."
                ),
                rationale=decision.rationale or "Pre-assigned TBD (discovery required).",
            )
            plan.phases.append(phase)

        else:
            logger.warning(
                "Unknown pre-assigned action '%s' — falling back to refactor path",
                action,
            )
            self._build_refactor_phases(plan)


def _phase_title(idx: int, role: str, module_count: int) -> str:
    labels = {
        "controller": "Extract outer API layer",
        "model": "Extract shared domain models",
        "service": "Extract business services",
        "repository": "Extract data access layer",
        "shared": "Untangle shared legacy libraries",
        "mainframe": "Wrap mainframe components",
        "unknown": "Audit and reclassify",
    }
    base = labels.get(role, role.title())
    return f"Phase {idx}: {base} ({module_count} module{'s' if module_count != 1 else ''})"


def _rollback_for_role(role: str) -> str:
    mapping = {
        "controller": "Switch API Gateway route back to legacy endpoints",
        "model": "Revert contracts package version; legacy model remains authoritative",
        "service": "Disable feature flag; traffic falls back to legacy service",
        "repository": "Remove anti-corruption layer; reads/writes resume on legacy schema",
        "shared": "Restore shared library import; republish legacy version",
        "mainframe": "Remove API adapter; clients resume direct JCL calls",
        "unknown": "Document the fall-back procedure before starting this phase",
    }
    return mapping.get(role, mapping["unknown"])


def _rationale_for_role(role: str, count: int, loc: int, vulns: int) -> str:
    desc = {
        "controller": (
            "Controllers are the outermost layer — they hold routing and input "
            "validation but no persistent state. Extracting them first lets us "
            "place a gateway over the legacy monolith and start splitting traffic."
        ),
        "model": (
            "Domain models are the contracts between caller and callee. "
            "Lifting them into a shared package unblocks parallel work on the "
            "dependent services."
        ),
        "service": (
            "Business services carry the core rules. Extracting them in this "
            "phase lets us run new implementations alongside legacy ones and "
            "validate parity before cut-over."
        ),
        "repository": (
            "Data access is high risk because schema changes require "
            "coordination with every consumer. We use an anti-corruption layer "
            "to decouple the new service from legacy SQL."
        ),
        "shared": (
            "Shared libraries are the hardest to extract — every consumer is "
            "affected. We handle them after leaf modules are stable so we can "
            "migrate consumers one at a time."
        ),
        "mainframe": (
            "Mainframe programs are expensive to rewrite and carry decades of "
            "business rules. We wrap them behind an API and treat them as "
            "dependencies until replacement is justified by a separate "
            "business case."
        ),
        "unknown": (
            "These modules could not be classified automatically. Audit them "
            "before starting extraction to determine the correct strangler "
            "strategy."
        ),
    }
    base = desc.get(role, desc["unknown"])
    return (
        f"{base} Scope: {count} module(s), "
        f"{loc:,} LOC, {vulns:,} known vulnerabilities."
    )


# ── Convenience async entry point ──────────────────────────────────────────


async def build_plan(
    project_path: str,
    name: str = "",
    *,
    discovery_context_path: str | Path | None = None,
    ecosystem_metrics_path: str | Path | None = None,
    load_default_ecosystem_metrics: bool = False,
    tenant_profile_path: str | Path | None = None,
    tenant_app_codename: str = "",
) -> StranglerPlan:
    """Ingest a project and return a strangler plan in one call.

    Args:
        project_path: filesystem path of the app to analyze.
        name: optional display name (defaults to the directory name).
        discovery_context_path: optional path to a directory containing
            ``analisis/`` (the corpus pipeline output). When provided,
            the planner enriches the plan with discovery findings:
            blockers, quick wins, corrections, and a risk-boost pass.
            Accepts either ``NexusForge-Shared/transcripciones-generales``
            or any directory that holds an ``analisis/`` subfolder.
        ecosystem_metrics_path: optional path to a
            ``tenant-alpha-ecosystem-health.yaml``-style fixture. When
            provided, the plan includes the app's priority score + rationale
            + critical density so ordering honors the ecosystem ranking.
        load_default_ecosystem_metrics: if True and ``ecosystem_metrics_path``
            is None, load the bundled fixture
            (``app/synth/fixtures/tenant-alpha-ecosystem-health.yaml``).
    """
    engine = RepoIngestionEngine()
    graph = await engine.ingest(project_path, name or Path(project_path).name)

    discovery_index = None
    if discovery_context_path is not None:
        try:
            from app.refactor.discovery_loader import load_discovery_context
            discovery_index = load_discovery_context(discovery_context_path)
            if discovery_index.total_findings == 0:
                logger.info(
                    "Discovery context at %s has 0 findings — skipping prior",
                    discovery_context_path,
                )
                discovery_index = None
        except Exception as exc:
            logger.warning(
                "Failed to load discovery context from %s: %s",
                discovery_context_path, exc,
            )
            discovery_index = None

    ecosystem_metrics = None
    if ecosystem_metrics_path is not None or load_default_ecosystem_metrics:
        try:
            from app.synth.ecosystem_metrics import load_ecosystem_metrics
            ecosystem_metrics = load_ecosystem_metrics(ecosystem_metrics_path)
            if not ecosystem_metrics.is_loaded():
                logger.info(
                    "Ecosystem metrics at %s is empty — skipping prior",
                    ecosystem_metrics_path,
                )
                ecosystem_metrics = None
        except Exception as exc:
            logger.warning(
                "Failed to load ecosystem metrics from %s: %s",
                ecosystem_metrics_path, exc,
            )
            ecosystem_metrics = None

    app_recipe = None
    if tenant_profile_path is not None:
        try:
            from app.synth.profile import load_profile
            profile = load_profile(tenant_profile_path)
            # Resolve the recipe by codename (preferred) or by loose match
            target_codename = tenant_app_codename or (name or Path(project_path).name)
            for app in profile.apps:
                if app.codename == target_codename:
                    app_recipe = app
                    break
            if app_recipe is None:
                lower = target_codename.lower()
                for app in profile.apps:
                    if app.codename.lower() in lower or lower in app.codename.lower():
                        app_recipe = app
                        break
            if app_recipe is None:
                logger.info(
                    "No recipe for codename %s in profile %s — skipping recipe priors",
                    target_codename, tenant_profile_path,
                )
        except Exception as exc:
            logger.warning(
                "Failed to load tenant profile from %s: %s",
                tenant_profile_path, exc,
            )
            app_recipe = None

    planner = StranglerPlanner(
        graph,
        discovery_index=discovery_index,
        ecosystem_metrics=ecosystem_metrics,
        app_recipe=app_recipe,
    )
    return planner.plan()


# ── Markdown rendering ─────────────────────────────────────────────────────


def render_markdown(plan: StranglerPlan) -> str:
    risk_icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}
    lines: list[str] = []
    lines.append(f"# Strangler Migration Plan — `{plan.app_name}`")
    lines.append("")
    lines.append(f"**App path:** `{plan.app_path}`")
    lines.append(f"**Total modules:** {plan.total_modules}")
    lines.append(f"**Total LOC:** {plan.total_loc:,}")
    lines.append(f"**Known vulnerabilities:** {plan.total_vulns:,}")
    lines.append(f"**Estimated effort:** {plan.total_effort_days} engineer-days")
    lines.append("")

    # P-018 — surface decision gate at the top when present so stakeholders
    # see the pending call before the phase plan.
    decision = plan.pre_assigned_decision
    if decision is not None and decision.is_gate:
        lines.append("## Decision gate — pending stakeholder call")
        lines.append("")
        gate_label = decision.gate_type or decision.action
        lines.append(f"**Gate type:** `{gate_label}`")
        if decision.blocker_to_resolve:
            lines.append(f"**Blocker to resolve:** {decision.blocker_to_resolve}")
        if decision.estimated_savings_if_taken:
            lines.append(
                f"**Estimated savings if taken:** {decision.estimated_savings_if_taken}"
            )
        if decision.stakeholders_to_confirm:
            lines.append(
                f"**Stakeholders to confirm:** "
                f"{', '.join(decision.stakeholders_to_confirm)}"
            )
        lines.append("")
        if decision.evidence_for:
            lines.append("**Evidence FOR the proposed action:**")
            for ev in decision.evidence_for:
                lines.append(f"- {ev}")
            lines.append("")
        if decision.evidence_against:
            lines.append("**Evidence AGAINST (blockers for the action):**")
            for ev in decision.evidence_against:
                lines.append(f"- {ev}")
            lines.append("")

    lines.append("## Narrative")
    lines.append("")
    lines.append(plan.narrative)
    lines.append("")
    lines.append("## Phases")
    lines.append("")
    for phase in plan.phases:
        lines.append(f"### {phase.title}")
        lines.append("")
        lines.append(f"**Risk:** {risk_icon.get(phase.risk, '⚪')} {phase.risk.upper()}")
        lines.append(f"**Effort:** ~{phase.effort_days} engineer-days")
        lines.append(f"**LOC in phase:** {phase.total_loc:,}")
        lines.append(f"**Vulnerabilities addressed:** {phase.total_vulns:,}")
        lines.append("")
        lines.append(f"**Rationale:** {phase.rationale}")
        lines.append("")
        lines.append(f"**Strategy:** {phase.strategy}")
        lines.append("")
        lines.append(f"**Rollback:** {phase.rollback}")
        lines.append("")
        if phase.modules:
            lines.append("**Modules in this phase:**")
            lines.append("")
            lines.append("| Module | LOC | Vulns | Depended-by |")
            lines.append("|---|---|---|---|")
            for m in phase.modules:
                lines.append(
                    f"| `{m.name}` | {m.lines_of_code:,} "
                    f"| {m.vulnerability_count:,} | {m.depended_by_count} |"
                )
            lines.append("")
    return "\n".join(lines)
