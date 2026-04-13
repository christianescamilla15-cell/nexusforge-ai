"""Tests for recipe-level priors in strangler_planner (B1 + B2).

Covers:
- MultiRobotPipeline.risk_level() → boosts phase 1 risk + surfaces recommendations
- OperationalProfile windows → summary string + scheduling guidance in narrative
- RegionalPolicy → warning list + narrative section
- No-recipe behavior is unchanged (pre-wire-up preserved)
- build_plan(tenant_profile_path=...) auto-resolves recipe by codename
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.refactor.ingestion import ModuleInfo, ProjectGraph
from app.refactor.strangler_planner import StranglerPlanner, build_plan
from app.synth.profile import (
    AppRecipe,
    MultiRobotPipeline,
    OperationalProfile,
    OperationalWindow,
    RegionalPolicy,
    SubProject,
    load_profile,
)


def _make_graph(name: str = "app-03") -> ProjectGraph:
    g = ProjectGraph(root=f"/tmp/{name}", name=name, total_lines=10_000)
    g.modules["web"] = ModuleInfo(
        name="web", path="/tmp/app/web", language="python",
        total_lines=6_000, vulnerability_count=30,
    )
    g.modules["api"] = ModuleInfo(
        name="api", path="/tmp/app/api", language="python",
        total_lines=4_000, vulnerability_count=20,
    )
    return g


# ── No-recipe (pre-B1/B2) behavior preserved ──────────────────────────


def test_planner_without_recipe_is_noop():
    planner = StranglerPlanner(_make_graph())
    plan = planner.plan()
    assert plan.multi_robot_risk == ""
    assert plan.multi_robot_recommendations == []
    assert plan.operational_windows_summary == ""
    assert plan.regional_policy_warnings == []
    assert "Multi-robot profile" not in plan.narrative
    assert "Operational profile" not in plan.narrative
    assert "Regional policies" not in plan.narrative


# ── MultiRobotPipeline surfacing ──────────────────────────────────────


def test_multi_robot_high_risk_surfaces_on_plan():
    recipe = AppRecipe(
        codename="app-03", label="Refunds",
        loc_target=80_000, primary_language="python",
        multi_robot=MultiRobotPipeline(
            robot_count=3,
            coordination="zmq-broker",
            stages=["download", "validate", "respond"],
            compensation_transactions=False,
            failure_detection="none",
            scraping_based=True,
            upstream_ui_owner="external-iata-bsplink",
        ),
    )
    plan = StranglerPlanner(_make_graph(), app_recipe=recipe).plan()

    assert plan.multi_robot_risk == "high"
    assert len(plan.multi_robot_recommendations) >= 3
    assert "Multi-robot profile" in plan.narrative
    assert "3 robots" in plan.narrative
    assert "zmq-broker" in plan.narrative
    assert "external-iata-bsplink" in plan.narrative


def test_multi_robot_high_risk_boosts_phase_one():
    """HIGH multi-robot risk should boost phase-1 risk or annotate it."""
    recipe = AppRecipe(
        codename="app-03", label="Refunds",
        loc_target=80_000, primary_language="python",
        multi_robot=MultiRobotPipeline(
            robot_count=3, coordination="zmq-broker",
            compensation_transactions=False,
            failure_detection="none",
            scraping_based=True,
        ),
    )
    plan = StranglerPlanner(_make_graph(), app_recipe=recipe).plan()
    assert len(plan.phases) >= 1
    first = plan.phases[0]
    boosted = "BOOSTED" in first.rationale or "HIGH risk" in first.rationale
    assert boosted


def test_multi_robot_low_risk_does_not_boost():
    recipe = AppRecipe(
        codename="app-03", label="Single robot",
        loc_target=10_000, primary_language="python",
        multi_robot=MultiRobotPipeline(
            robot_count=1, coordination="direct-rpc",
            compensation_transactions=True, failure_detection="health-check",
        ),
    )
    plan = StranglerPlanner(_make_graph(), app_recipe=recipe).plan()
    assert plan.multi_robot_risk == "low"
    assert plan.multi_robot_recommendations == []
    for phase in plan.phases:
        assert "BOOSTED" not in phase.rationale


# ── OperationalProfile surfacing ──────────────────────────────────────


def test_operational_profile_surfaces_summary():
    op = OperationalProfile(
        user_count=81,
        user_roles=["atencion-clientes", "camepa"],
        daily_request_volume=500,
        operational_windows=[
            OperationalWindow(start="08:00", end="11:00", region="MX"),
            OperationalWindow(start="11:00", end="14:00", region="MX"),
            OperationalWindow(start="14:00", end="17:00", region="MX"),
            OperationalWindow(start="17:00", end="20:00", region="MX"),
        ],
        vpn_required=True,
        mfa_required=True,
    )
    recipe = AppRecipe(
        codename="app-03", label="Refunds",
        loc_target=80_000, primary_language="python",
        sub_projects=[
            SubProject(name="reembolsos-especiales", language="python", operational=op),
        ],
    )
    plan = StranglerPlanner(_make_graph(), app_recipe=recipe).plan()

    assert "81 users" in plan.operational_windows_summary
    assert "500/day" in plan.operational_windows_summary
    assert "VPN" in plan.operational_windows_summary
    assert "MFA" in plan.operational_windows_summary

    assert "Operational profile" in plan.narrative
    assert "reembolsos-especiales" in plan.narrative
    assert "Scheduling guidance" in plan.narrative


def test_operational_profile_absent_for_sub_projects_without_it():
    recipe = AppRecipe(
        codename="app-03", label="No op",
        loc_target=80_000, primary_language="python",
        sub_projects=[SubProject(name="backend", language="python")],
    )
    plan = StranglerPlanner(_make_graph(), app_recipe=recipe).plan()
    assert plan.operational_windows_summary == ""
    assert "Operational profile" not in plan.narrative


# ── RegionalPolicy surfacing ──────────────────────────────────────────


def test_regional_policy_hardcoded_surfaces_as_warning():
    recipe = AppRecipe(
        codename="app-03", label="Refunds",
        loc_target=80_000, primary_language="python",
        regional_policies=[
            RegionalPolicy(
                region_scope="country",
                regions=["BR", "RU", "MX"],
                policy_type="refund-rules",
                externalization="hardcoded",
            ),
        ],
    )
    plan = StranglerPlanner(_make_graph(), app_recipe=recipe).plan()

    assert len(plan.regional_policy_warnings) == 1
    warn = plan.regional_policy_warnings[0]
    assert "refund-rules" in warn
    assert "BR" in warn and "RU" in warn
    assert "hardcoded" in warn or "Hardcoded" in warn

    assert "Regional policies" in plan.narrative


def test_regional_policy_rules_engine_recognized_as_terminal():
    recipe = AppRecipe(
        codename="app-03", label="Target state",
        loc_target=80_000, primary_language="python",
        regional_policies=[
            RegionalPolicy(
                regions=["BR"], policy_type="refund-rules",
                externalization="rules-engine",
            ),
        ],
    )
    plan = StranglerPlanner(_make_graph(), app_recipe=recipe).plan()
    assert "Target state reached" in plan.regional_policy_warnings[0]


# ── All three priors together ─────────────────────────────────────────


def test_all_recipe_priors_coexist_in_narrative():
    recipe = AppRecipe(
        codename="app-03", label="Everything",
        loc_target=80_000, primary_language="python",
        multi_robot=MultiRobotPipeline(
            robot_count=3, coordination="zmq-broker",
            compensation_transactions=False, scraping_based=True,
        ),
        sub_projects=[
            SubProject(
                name="special", language="python",
                operational=OperationalProfile(
                    user_count=81,
                    operational_windows=[OperationalWindow(start="08:00", end="20:00", region="MX")],
                ),
            ),
        ],
        regional_policies=[
            RegionalPolicy(regions=["BR"], policy_type="refund-rules", externalization="hardcoded"),
        ],
    )
    plan = StranglerPlanner(_make_graph(), app_recipe=recipe).plan()
    assert "Multi-robot profile" in plan.narrative
    assert "Operational profile" in plan.narrative
    assert "Regional policies" in plan.narrative


def test_recipe_priors_are_reflected_in_to_dict():
    recipe = AppRecipe(
        codename="app-03", label="Dict",
        loc_target=80_000, primary_language="python",
        multi_robot=MultiRobotPipeline(robot_count=3, compensation_transactions=False, scraping_based=True),
    )
    plan = StranglerPlanner(_make_graph(), app_recipe=recipe).plan()
    d = plan.to_dict()
    assert "multi_robot_risk" in d
    assert "multi_robot_recommendations" in d
    assert "operational_windows_summary" in d
    assert "regional_policy_warnings" in d


# ── build_plan wire-up ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_plan_resolves_recipe_from_profile(tmp_path):
    """build_plan(tenant_profile_path=…) loads tenant_alpha.yaml and surfaces priors."""
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("x = 1\n", encoding="utf-8")

    fixture = (
        Path(__file__).parent.parent
        / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
    )

    plan = await build_plan(
        str(project),
        name="app-03",
        tenant_profile_path=str(fixture),
        tenant_app_codename="app-03",
    )
    # tenant_alpha app-03 has multi_robot + operational + regional_policies
    assert plan.multi_robot_risk == "high"
    assert plan.operational_windows_summary != ""
    assert len(plan.regional_policy_warnings) >= 1


@pytest.mark.asyncio
async def test_build_plan_unknown_codename_silently_degrades(tmp_path):
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("y = 2\n", encoding="utf-8")

    fixture = (
        Path(__file__).parent.parent
        / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
    )

    plan = await build_plan(
        str(project),
        name="unknown-app",
        tenant_profile_path=str(fixture),
        tenant_app_codename="does-not-exist",
    )
    # No match → no recipe priors attached
    assert plan.multi_robot_risk == ""
    assert plan.operational_windows_summary == ""


@pytest.mark.asyncio
async def test_build_plan_without_tenant_profile_is_silent(tmp_path):
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "main.py").write_text("z = 3\n", encoding="utf-8")

    plan = await build_plan(str(project), name="myapp")
    assert plan.multi_robot_risk == ""
    assert plan.operational_windows_summary == ""
    assert plan.regional_policy_warnings == []
