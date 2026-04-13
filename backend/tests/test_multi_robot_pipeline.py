"""Tests for MultiRobotPipeline (P-019).

Covers:
- Risk level heuristic (signal count → low/medium/high)
- Recommendation generation (concrete refactor suggestions)
- YAML parsing from tenant_alpha.yaml (app-03 multi_robot block)
- AppRecipe optional attachment (absent by default)
"""
from __future__ import annotations

from pathlib import Path

from app.synth.profile import (
    AppRecipe,
    MultiRobotPipeline,
    load_profile,
)


# ── Dataclass defaults ────────────────────────────────────────────────


def test_multi_robot_defaults_are_safe():
    mr = MultiRobotPipeline()
    assert mr.robot_count == 1
    assert mr.coordination == "none"
    assert mr.stages == []
    assert mr.compensation_transactions is False
    assert mr.scraping_based is False


def test_app_recipe_does_not_have_multi_robot_by_default():
    r = AppRecipe(
        codename="foo",
        label="Foo",
        loc_target=10_000,
        primary_language="python",
    )
    assert r.multi_robot is None


# ── Risk heuristic ────────────────────────────────────────────────────


def test_risk_high_for_app_03_bsp_profile():
    """A BSP-style pipeline (3 robots, scraping, no compensation, no health-check) → HIGH."""
    mr = MultiRobotPipeline(
        robot_count=3,
        coordination="zmq-broker",
        stages=["download", "validate", "respond"],
        compensation_transactions=False,
        failure_detection="none",
        scraping_based=True,
        upstream_ui_owner="external-iata-bsplink",
    )
    assert mr.risk_level() == "high"


def test_risk_low_for_safe_single_robot():
    mr = MultiRobotPipeline(
        robot_count=1,
        coordination="direct-rpc",
        compensation_transactions=True,
        failure_detection="health-check",
        scraping_based=False,
    )
    assert mr.risk_level() == "low"


def test_risk_medium_for_partial_signals():
    mr = MultiRobotPipeline(
        robot_count=2,
        coordination="redis-queue",
        compensation_transactions=False,
        failure_detection="none",
        scraping_based=False,
    )
    # 2 signals: no compensation (2) + no detection (1) = 3 → medium
    assert mr.risk_level() == "medium"


# ── Recommendations ───────────────────────────────────────────────────


def test_recommendations_for_bsp_profile_include_all_four():
    mr = MultiRobotPipeline(
        robot_count=3,
        coordination="zmq-broker",
        compensation_transactions=False,
        failure_detection="none",
        scraping_based=True,
        upstream_ui_owner="external-iata-bsplink",
    )
    recs = mr.recommendations()
    text = " ".join(recs).lower()
    assert "compensation" in text
    assert "contract test" in text or "contract-test" in text
    assert "health-check" in text or "silent" in text
    # coordination is set to zmq-broker, so no broker recommendation
    assert "message broker" not in text


def test_recommendations_empty_for_safe_profile():
    mr = MultiRobotPipeline(
        robot_count=1,
        coordination="direct-rpc",
        compensation_transactions=True,
        failure_detection="health-check",
        scraping_based=False,
    )
    assert mr.recommendations() == []


def test_recommendations_add_broker_when_no_coordination_and_multiple_robots():
    mr = MultiRobotPipeline(
        robot_count=3,
        coordination="none",
        compensation_transactions=True,
        failure_detection="health-check",
        scraping_based=False,
    )
    recs = mr.recommendations()
    text = " ".join(recs).lower()
    assert "message broker" in text or "broker" in text


# ── YAML parsing from tenant_alpha.yaml ──────────────────────────────


def test_tenant_alpha_yaml_exposes_multi_robot_for_app_03():
    """The committed fixture must declare the BSP-style pipeline on app-03."""
    fixture = (
        Path(__file__).parent.parent
        / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
    )
    profile = load_profile(fixture)

    app03 = next((a for a in profile.apps if a.codename == "app-03"), None)
    assert app03 is not None
    assert app03.multi_robot is not None
    mr = app03.multi_robot
    assert mr.robot_count == 3
    assert mr.coordination == "zmq-broker"
    assert len(mr.stages) == 3
    assert mr.compensation_transactions is False
    assert mr.scraping_based is True
    assert mr.upstream_ui_owner == "external-iata-bsplink"
    assert mr.risk_level() == "high"
    # Has at least 3 recommendations (compensation + contract + health-check)
    assert len(mr.recommendations()) >= 3


def test_other_apps_do_not_have_multi_robot():
    """Multi-robot is opt-in; only app-03 declares it in the fixture."""
    fixture = (
        Path(__file__).parent.parent
        / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
    )
    profile = load_profile(fixture)
    for app in profile.apps:
        if app.codename == "app-03":
            continue
        assert app.multi_robot is None, (
            f"{app.codename} unexpectedly has multi_robot block"
        )
