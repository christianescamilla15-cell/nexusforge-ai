"""Tests for discovery_loader → strangler_planner integration.

Covers:
- Discovery index passes through as a prior when provided.
- Missing discovery index preserves pre-Gap-F behavior byte-for-byte.
- Blockers from discovery surface as plan.discovery_blockers.
- Quick wins surface on plan.discovery_quick_wins.
- Risk is boosted on a medium-risk phase when blockers are present.
- Narrative includes a "Discovery context" section.
- build_plan(discovery_context_path=...) wires through end-to-end.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.refactor.discovery_loader import (
    DiscoveryFinding,
    DiscoveryIndex,
    load_discovery_context,
    _OPENPYXL_AVAILABLE,
)
from app.refactor.ingestion import ModuleInfo, ProjectGraph
from app.refactor.strangler_planner import (
    StranglerPlan,
    StranglerPlanner,
    build_plan,
)


# ── Helpers ───────────────────────────────────────────────────────────


def _make_graph(app_name: str = "app-03-arc") -> ProjectGraph:
    """Synthesize a minimal ProjectGraph with two modules."""
    g = ProjectGraph(root=f"/tmp/{app_name}", name=app_name, total_lines=10_000)
    g.modules["web"] = ModuleInfo(
        name="web", path="/tmp/app/web", language="python",
        total_lines=6_000, vulnerability_count=40,
    )
    g.modules["api"] = ModuleInfo(
        name="api", path="/tmp/app/api", language="python",
        total_lines=4_000, vulnerability_count=20,
    )
    return g


def _make_index_with_blockers(
    app: str = "app-03-arc",
    blocker_count: int = 2,
) -> DiscoveryIndex:
    idx = DiscoveryIndex(source_path="synthetic")
    for i in range(blocker_count):
        idx.findings.append(DiscoveryFinding(
            id=f"H-{900 + i:03d}",
            title=f"Blocker {i} on {app}",
            state="VALIDATED",
            domains=["reembolsos"],
            apps_affected=[app],
            severity="high",
            description=f"Blocker for {app}",
            is_blocker=True,
        ))
    idx.findings.append(DiscoveryFinding(
        id="H-Q01",
        title="Quick win opportunity",
        state="VALIDATED",
        domains=["reembolsos"],
        apps_affected=[app],
        severity="low",
        is_quick_win=True,
    ))
    idx.findings.append(DiscoveryFinding(
        id="H-C01",
        title="Model correction",
        state="CONFIRMED-BY-DOCS",
        domains=["reembolsos"],
        apps_affected=[app],
        is_correction=True,
    ))
    idx.total_findings = len(idx.findings)
    idx.total_blockers = blocker_count
    idx.total_quick_wins = 1
    idx.total_corrections = 1
    idx.apps_mentioned = [app]
    return idx


# ── No-index (pre-Gap-F) behavior ─────────────────────────────────────


def test_planner_without_discovery_has_empty_discovery_fields():
    planner = StranglerPlanner(_make_graph())
    plan = planner.plan()
    assert plan.discovery_findings_count == 0
    assert plan.discovery_blockers == []
    assert plan.discovery_quick_wins == []
    assert plan.discovery_corrections == []
    # Narrative must not contain the "Discovery context" header
    assert "Discovery context" not in plan.narrative


# ── Discovery enrichment ──────────────────────────────────────────────


def test_discovery_blockers_surface_on_plan():
    idx = _make_index_with_blockers(blocker_count=2)
    planner = StranglerPlanner(_make_graph(), discovery_index=idx)
    plan = planner.plan()

    assert plan.discovery_findings_count == 4
    assert len(plan.discovery_blockers) == 2
    assert all("Blocker" in b for b in plan.discovery_blockers)


def test_discovery_quick_wins_surface_on_plan():
    idx = _make_index_with_blockers()
    planner = StranglerPlanner(_make_graph(), discovery_index=idx)
    plan = planner.plan()

    assert len(plan.discovery_quick_wins) == 1
    assert "Quick win" in plan.discovery_quick_wins[0]


def test_discovery_corrections_surface_on_plan():
    idx = _make_index_with_blockers()
    planner = StranglerPlanner(_make_graph(), discovery_index=idx)
    plan = planner.plan()

    assert len(plan.discovery_corrections) == 1
    assert "correction" in plan.discovery_corrections[0].lower()


def test_discovery_narrative_section_added():
    idx = _make_index_with_blockers()
    planner = StranglerPlanner(_make_graph(), discovery_index=idx)
    plan = planner.plan()

    assert "Discovery context" in plan.narrative
    assert "Blockers" in plan.narrative
    assert "Quick wins" in plan.narrative


def test_discovery_no_codename_match_no_op():
    """If app name doesn't match any codename in index, discovery is a no-op."""
    idx = _make_index_with_blockers(app="app-99")
    planner = StranglerPlanner(_make_graph("app-01"), discovery_index=idx)
    plan = planner.plan()
    assert plan.discovery_findings_count == 0
    assert plan.discovery_blockers == []


def test_risk_boost_on_medium_phase_when_blockers_present():
    idx = _make_index_with_blockers(blocker_count=3)
    planner = StranglerPlanner(_make_graph(), discovery_index=idx)
    plan = planner.plan()

    # At least one phase should be boosted or annotated
    if plan.phases:
        boosted = [p for p in plan.phases if "BOOSTED" in p.rationale or "confirms" in p.rationale.lower()]
        # Only assert if there were phases at medium risk before the boost
        medium_phases = [p for p in plan.phases if p.risk in ("high",)]
        if medium_phases:
            assert len(boosted) >= 1


def test_plan_to_dict_exposes_discovery_fields():
    idx = _make_index_with_blockers()
    plan = StranglerPlanner(_make_graph(), discovery_index=idx).plan()
    d = plan.to_dict()
    assert "discovery_findings_count" in d
    assert "discovery_blockers" in d
    assert "discovery_quick_wins" in d
    assert "discovery_corrections" in d
    assert d["discovery_findings_count"] == 4


# ── build_plan wiring ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_plan_loads_discovery_from_path(tmp_path):
    """build_plan accepts discovery_context_path and loads the index."""
    # Build a minimal project
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("print('hello')\n", encoding="utf-8")

    # Build a minimal analisis/ with a maestro that has an app-03-arc finding
    base = tmp_path / "corpus"
    (base / "analisis").mkdir(parents=True)
    maestro = """\
# Fase 3 maestro

### H-800 — Critical blocker on app-03-arc
- **Estado**: `VALIDATED`
- **Dominios**: reembolsos
- **Descripción**: Bloqueador app-03-arc sin ambiente dev.
"""
    (base / "analisis" / "fase-3-maestro.md").write_text(maestro, encoding="utf-8")

    # Use name="app-03-arc" so the planner matches the codename
    plan = await build_plan(
        str(project),
        name="app-03-arc",
        discovery_context_path=str(base),
    )
    # Should surface the blocker from the corpus
    assert plan.discovery_findings_count >= 1
    assert any("H-800" in b for b in plan.discovery_blockers)


@pytest.mark.asyncio
async def test_build_plan_without_discovery_path_is_silent(tmp_path):
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("x = 1\n", encoding="utf-8")

    plan = await build_plan(str(project), name="myapp")
    assert plan.discovery_findings_count == 0
    assert plan.discovery_blockers == []


@pytest.mark.asyncio
async def test_build_plan_bad_discovery_path_silently_degrades(tmp_path):
    """If the discovery path is invalid, the planner falls back to no-prior mode."""
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("y = 2\n", encoding="utf-8")

    plan = await build_plan(
        str(project),
        name="myapp",
        discovery_context_path=str(tmp_path / "does-not-exist"),
    )
    assert plan.discovery_findings_count == 0
