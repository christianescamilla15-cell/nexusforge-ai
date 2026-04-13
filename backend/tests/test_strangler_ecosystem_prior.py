"""Tests for EcosystemMetrics → strangler_planner integration (P-021 wire-up)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.refactor.ingestion import ModuleInfo, ProjectGraph
from app.refactor.strangler_planner import StranglerPlanner, build_plan
from app.synth.ecosystem_metrics import (
    AppCriticalDensity,
    EcosystemMetrics,
    PriorityHint,
    load_ecosystem_metrics,
    _YAML_AVAILABLE,
)


def _make_graph(name: str = "app-03-arc") -> ProjectGraph:
    g = ProjectGraph(root=f"/tmp/{name}", name=name, total_lines=10_000)
    g.modules["web"] = ModuleInfo(
        name="web", path="/tmp/app/web", language="python",
        total_lines=10_000, vulnerability_count=30,
    )
    return g


def _make_metrics(codename: str = "app-03-arc") -> EcosystemMetrics:
    m = EcosystemMetrics(version="test", tenant_id="tenant-alpha")
    m.total_loc = 5_634_738
    m.total_issues = 189_997
    m.risk_total_usd = 18_500_000
    m.per_app.append(AppCriticalDensity(
        app=codename, label="Test app",
        total_issues=13, critical_issues=9,
        blocker_issues=0, critical_density_pct=69.2,
        hosting="on-premise",
    ))
    m.priority_hints.append(PriorityHint(
        app=codename, priority_score=50.8,
        rationale="Highest criticality density in ecosystem",
    ))
    m._loaded = True
    return m


# ── No-prior (pre-P-021) behavior ────────────────────────────────────


def test_planner_without_ecosystem_leaves_fields_zero():
    planner = StranglerPlanner(_make_graph())
    plan = planner.plan()
    assert plan.ecosystem_priority_score == 0.0
    assert plan.ecosystem_priority_rationale == ""
    assert plan.ecosystem_critical_density_pct == 0.0
    assert "Ecosystem prior" not in plan.narrative


# ── Ecosystem prior applied ──────────────────────────────────────────


def test_ecosystem_priority_surfaces_on_plan():
    metrics = _make_metrics()
    planner = StranglerPlanner(_make_graph(), ecosystem_metrics=metrics)
    plan = planner.plan()
    assert plan.ecosystem_priority_score == pytest.approx(50.8)
    assert "Highest criticality" in plan.ecosystem_priority_rationale
    assert plan.ecosystem_critical_density_pct == pytest.approx(69.2)
    assert plan.ecosystem_hosting == "on-premise"
    assert plan.ecosystem_risk_total_usd == 18_500_000


def test_ecosystem_narrative_section_added():
    metrics = _make_metrics()
    planner = StranglerPlanner(_make_graph(), ecosystem_metrics=metrics)
    plan = planner.plan()
    assert "Ecosystem prior" in plan.narrative
    assert "Priority score" in plan.narrative
    assert "Critical density" in plan.narrative


def test_ecosystem_no_match_is_no_op():
    metrics = _make_metrics(codename="app-99")
    planner = StranglerPlanner(_make_graph("app-01"), ecosystem_metrics=metrics)
    plan = planner.plan()
    assert plan.ecosystem_priority_score == 0.0


def test_ecosystem_field_in_to_dict():
    metrics = _make_metrics()
    plan = StranglerPlanner(_make_graph(), ecosystem_metrics=metrics).plan()
    d = plan.to_dict()
    assert "ecosystem_priority_score" in d
    assert d["ecosystem_priority_score"] == pytest.approx(50.8)
    assert d["ecosystem_risk_total_usd"] == 18_500_000


# ── build_plan wiring ────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
async def test_build_plan_loads_default_ecosystem_metrics(tmp_path):
    """build_plan(load_default_ecosystem_metrics=True) auto-loads fixture."""
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("print(1)\n", encoding="utf-8")

    plan = await build_plan(
        str(project),
        name="app-03-arc",
        load_default_ecosystem_metrics=True,
    )
    assert plan.ecosystem_priority_score > 0.0
    assert plan.ecosystem_risk_total_usd == 18_500_000


@pytest.mark.asyncio
async def test_build_plan_without_ecosystem_is_silent(tmp_path):
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("x = 1\n", encoding="utf-8")

    plan = await build_plan(str(project), name="myapp")
    assert plan.ecosystem_priority_score == 0.0
    assert "Ecosystem prior" not in plan.narrative


@pytest.mark.asyncio
async def test_build_plan_bad_ecosystem_path_degrades_silently(tmp_path):
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("y = 2\n", encoding="utf-8")

    plan = await build_plan(
        str(project),
        name="myapp",
        ecosystem_metrics_path=str(tmp_path / "missing.yaml"),
    )
    assert plan.ecosystem_priority_score == 0.0


@pytest.mark.asyncio
@pytest.mark.skipif(not _YAML_AVAILABLE, reason="PyYAML not installed")
async def test_build_plan_with_discovery_and_ecosystem_together(tmp_path):
    """Both priors can coexist; they attach to the same codename."""
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("z = 3\n", encoding="utf-8")

    # Minimal discovery corpus
    base = tmp_path / "corpus"
    (base / "analisis").mkdir(parents=True)
    (base / "analisis" / "fase-3-maestro.md").write_text(
        "### H-500 — Critical blocker on app-03-arc\n"
        "- **Estado**: `VALIDATED`\n"
        "- **Dominios**: reembolsos\n"
        "- **Descripción**: Bloqueador app-03-arc sin ambiente dev.\n",
        encoding="utf-8",
    )

    plan = await build_plan(
        str(project),
        name="app-03-arc",
        discovery_context_path=str(base),
        load_default_ecosystem_metrics=True,
    )

    # Discovery prior attached
    assert plan.discovery_findings_count >= 1
    # Ecosystem prior attached
    assert plan.ecosystem_priority_score > 0.0
    # Both narrative sections present
    assert "Discovery context" in plan.narrative
    assert "Ecosystem prior" in plan.narrative
