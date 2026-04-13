"""Tests for OperationalProfile (P-012)."""
from __future__ import annotations

from pathlib import Path

from app.synth.profile import (
    OperationalProfile,
    OperationalWindow,
    SubProject,
    load_profile,
)


FIXTURE = (
    Path(__file__).parent.parent
    / "app" / "synth" / "fixtures" / "tenant_alpha.yaml"
)


# ── Dataclass defaults ────────────────────────────────────────────────


def test_operational_profile_defaults():
    op = OperationalProfile()
    assert op.user_count == 0
    assert op.operational_windows == []
    assert op.planned_integrations == []


def test_operational_window_defaults():
    w = OperationalWindow()
    assert w.start == ""
    assert w.end == ""


def test_sub_project_operational_defaults_none():
    sp = SubProject(name="foo", language="python")
    assert sp.operational is None


# ── YAML wiring — app-03 reembolsos-especiales sub-project ────────────


def test_reembolsos_especiales_has_operational_profile():
    profile = load_profile(FIXTURE)
    app03 = next(a for a in profile.apps if a.codename == "app-03")
    especiales = next(
        sp for sp in app03.sub_projects if sp.name == "reembolsos-especiales"
    )
    assert especiales.operational is not None

    op = especiales.operational
    # Workshop W2 confirmed 81 users + 500/day + 4 windows + VPN + 2FA
    assert op.user_count == 81
    assert op.daily_request_volume == 500
    assert len(op.operational_windows) == 4
    assert op.vpn_required is True
    assert op.mfa_required is True

    # User roles observed in the workshop
    roles = set(op.user_roles)
    assert "atencion-clientes" in roles
    assert "camepa" in roles

    # Planned integration with RAM (H-157)
    assert "ram-refunds" in op.planned_integrations


def test_operational_windows_cover_morning_to_evening():
    profile = load_profile(FIXTURE)
    app03 = next(a for a in profile.apps if a.codename == "app-03")
    especiales = next(
        sp for sp in app03.sub_projects if sp.name == "reembolsos-especiales"
    )
    windows = especiales.operational.operational_windows
    starts = [w.start for w in windows]
    # Confirmed schedule: 08:00 → 20:00 in 4 consecutive slots
    assert "08:00" in starts
    assert "17:00" in starts
    # All Mexico region
    regions = {w.region for w in windows}
    assert regions == {"MX"}


def test_other_sub_projects_do_not_declare_operational():
    profile = load_profile(FIXTURE)
    app03 = next(a for a in profile.apps if a.codename == "app-03")
    for sp in app03.sub_projects:
        if sp.name == "reembolsos-especiales":
            continue
        assert sp.operational is None, (
            f"sub-project {sp.name} unexpectedly has operational profile"
        )
