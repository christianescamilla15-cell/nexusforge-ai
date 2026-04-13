"""Tests for decision-gate framework (P-018 / Gap T).

Covers:
- RefactorDecision defaults do NOT form a gate.
- is_gate True when gate_type set or action=='tbd'.
- Markdown output includes a "Decision gate" section when is_gate.
- tenant_alpha.yaml app-03 wires the retire-vs-refactor gate correctly.
"""
from __future__ import annotations

from pathlib import Path

from app.synth.profile import RefactorDecision, load_profile


FIXTURE = (
    Path(__file__).parent.parent
    / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
)


# ── Dataclass behavior ────────────────────────────────────────────────


def test_default_decision_is_not_a_gate():
    d = RefactorDecision()
    assert d.is_gate is False
    assert d.evidence_for == []
    assert d.evidence_against == []
    assert d.blocker_to_resolve == ""


def test_tbd_action_marks_as_gate():
    d = RefactorDecision(action="tbd", phase="IMMEDIATE")
    assert d.is_gate is True


def test_explicit_gate_type_marks_as_gate():
    d = RefactorDecision(action="refactor", gate_type="retire-vs-refactor")
    assert d.is_gate is True


def test_markdown_without_gate_has_no_gate_section():
    d = RefactorDecision(
        action="refactor",
        phase="Q3",
        rationale="Clean refactor",
        validation_checklist=["item-1"],
    )
    md = d.to_markdown("app-07", "Example App")
    assert "Decision gate" not in md
    assert "**Action:** `REFACTOR`" in md


def test_markdown_with_gate_has_gate_section():
    d = RefactorDecision(
        action="tbd",
        phase="IMMEDIATE",
        rationale="Needs owner confirmation",
        gate_type="retire-vs-refactor",
        evidence_for=["0% activity since 2023"],
        evidence_against=["Business owner not confirmed"],
        blocker_to_resolve="Escalate to business owner",
        estimated_savings_if_taken="~4 weeks",
        stakeholders_to_confirm=["cliente-owner", "compliance"],
    )
    md = d.to_markdown("app-03", "Automated Refund Processing")
    assert "Decision gate" in md
    assert "retire-vs-refactor" in md
    assert "Evidence FOR" in md and "Evidence AGAINST" in md
    assert "0% activity since 2023" in md
    assert "Escalate to business owner" in md
    assert "cliente-owner" in md


# ── YAML wiring ────────────────────────────────────────────────────────


def test_app_03_has_retire_gate_from_yaml():
    profile = load_profile(FIXTURE)
    app03 = next(a for a in profile.apps if a.codename == "app-03")
    assert app03.decision is not None
    d = app03.decision
    assert d.is_gate is True
    assert d.gate_type == "retire-vs-refactor"
    assert any("0%" in e for e in d.evidence_for)
    assert any("business owner" in e.lower() for e in d.evidence_against)
    assert "business owner" in d.blocker_to_resolve.lower() or "compliance" in d.blocker_to_resolve.lower()
    assert len(d.stakeholders_to_confirm) >= 2


def test_other_apps_do_not_have_gate():
    profile = load_profile(FIXTURE)
    for app in profile.apps:
        if app.codename == "app-03" or app.codename == "app-04":
            continue  # app-04 has decision.action=tbd → is_gate True; skip it
        if app.decision is None:
            continue
        assert app.decision.is_gate is False, (
            f"{app.codename} unexpectedly has a decision gate"
        )
