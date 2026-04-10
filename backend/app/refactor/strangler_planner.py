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

from .ingestion import ProjectGraph, RepoIngestionEngine

logger = logging.getLogger(__name__)


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
    """Produces a strangler-pattern migration plan for a single app."""

    def __init__(self, graph: ProjectGraph):
        self.graph = graph

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
            return plan

        # Default refactor path — group modules by role
        self._build_refactor_phases(plan)
        plan.narrative = _build_narrative_with_decision(plan, decision)
        return plan

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


async def build_plan(project_path: str, name: str = "") -> StranglerPlan:
    """Ingest a project and return a strangler plan in one call."""
    engine = RepoIngestionEngine()
    graph = await engine.ingest(project_path, name or Path(project_path).name)
    planner = StranglerPlanner(graph)
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
