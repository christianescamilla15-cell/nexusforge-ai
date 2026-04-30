"""Tests for `_compute_next_run` in app/routes/automations.py.

T3.2 from the 2026-04-30 triangulation. Until that commit the
scheduler used a homegrown parser that only honored the minute
and hour fields and IGNORED day-of-month, month, and day-of-week.
The result: any cron expression that restricted to weekdays,
specific months, or specific days would also fire on every other
day. We replaced the homegrown parser with `croniter`; these tests
pin the previously-broken cases.

All cases use a fixed `now` so they're deterministic regardless of
what wall-clock time the suite runs at.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.routes.automations import _compute_next_run


# ─── helpers ─────────────────────────────────────────────────────────


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# ─── DOW restriction (the canonical regression) ──────────────────────


def test_weekday_only_cron_skips_weekends():
    """`30 9 * * 1-5` = 9:30 Monday-Friday. Previously, calling on
    Friday would advance to Saturday because DOW was ignored. Now
    croniter correctly skips to Monday."""
    # Friday 2026-05-01 10:00 UTC — past the day's 9:30 firing.
    friday_after_fire = _utc(2026, 5, 1, 10, 0)
    assert friday_after_fire.weekday() == 4  # 0=Mon, 4=Fri

    next_run = _compute_next_run("30 9 * * 1-5", now=friday_after_fire)
    # Should be Monday 2026-05-04 09:30 UTC, NOT Saturday.
    assert next_run.weekday() == 0  # Monday
    assert next_run.hour == 9 and next_run.minute == 30
    assert (next_run - friday_after_fire) >= timedelta(days=2)


def test_weekday_only_cron_advances_to_next_business_day():
    """Saturday → next firing must be Monday (DOW filter active)."""
    saturday = _utc(2026, 5, 2, 0, 0)
    assert saturday.weekday() == 5  # Saturday

    next_run = _compute_next_run("0 0 * * 1-5", now=saturday)
    assert next_run.weekday() == 0  # Monday
    # ~2 days later (Sun + Mon midnight).
    assert next_run.date() > saturday.date()


# ─── DOM restriction ─────────────────────────────────────────────────


def test_first_of_month_only(monkeypatch=None):
    """`0 12 1 * *` = noon on the 1st of every month. Mid-month
    'now' must advance to the 1st of the next month, not tomorrow."""
    mid_month = _utc(2026, 5, 15, 13, 0)
    next_run = _compute_next_run("0 12 1 * *", now=mid_month)
    assert next_run.day == 1
    assert next_run.month == 6  # next month, not the same one
    assert next_run.hour == 12 and next_run.minute == 0


# ─── month restriction ───────────────────────────────────────────────


def test_january_only_cron_advances_to_next_january():
    """`0 0 1 1 *` = midnight Jan 1. From mid-year 'now', must
    skip the rest of the calendar year, not fire each month."""
    july = _utc(2026, 7, 15, 0, 0)
    next_run = _compute_next_run("0 0 1 1 *", now=july)
    assert next_run.year == 2027
    assert next_run.month == 1
    assert next_run.day == 1


# ─── existing legitimate patterns still work ─────────────────────────


def test_every_n_minutes_pattern_preserved():
    """`*/15 * * * *` — common "every 15 minutes" pattern. Used to
    work in the homegrown parser; verify croniter doesn't break it."""
    now = _utc(2026, 5, 1, 10, 7)  # 10:07
    next_run = _compute_next_run("*/15 * * * *", now=now)
    # Next quarter-hour after 10:07 is 10:15.
    assert next_run.minute == 15
    assert next_run.hour == 10


def test_daily_at_fixed_time():
    """`0 9 * * *` — daily at 9:00. Sanity that the canonical
    daily case still produces tomorrow when 'now' is past 9:00."""
    now = _utc(2026, 5, 1, 10, 0)  # past today's 9:00 firing
    next_run = _compute_next_run("0 9 * * *", now=now)
    assert next_run.hour == 9
    assert next_run.minute == 0
    # Should be the NEXT day, not today.
    assert next_run.date() > now.date()


# ─── error paths ─────────────────────────────────────────────────────


def test_invalid_cron_falls_back_to_one_hour():
    """A malformed expression returns now+1h instead of crashing
    the scheduler loop. Same fail-soft contract as the old parser."""
    now = _utc(2026, 5, 1, 10, 0)
    next_run = _compute_next_run("not a cron expression", now=now)
    assert next_run == now + timedelta(hours=1)


def test_empty_cron_falls_back_to_one_hour():
    now = _utc(2026, 5, 1, 10, 0)
    assert _compute_next_run("", now=now) == now + timedelta(hours=1)
    assert _compute_next_run("   ", now=now) == now + timedelta(hours=1)


def test_cron_with_too_few_fields_falls_back():
    """The old parser checked `len(parts) != 5` and returned
    now+1h. croniter raises ValueError on the same input. The
    wrapper must still return now+1h, not propagate the exception."""
    now = _utc(2026, 5, 1, 10, 0)
    assert _compute_next_run("0 9 *", now=now) == now + timedelta(hours=1)
    assert _compute_next_run("0", now=now) == now + timedelta(hours=1)


# ─── DST-safety / timezone hygiene ───────────────────────────────────


def test_returns_timezone_aware_utc():
    """All callers store next_run_at into Postgres TIMESTAMPTZ — a
    naive datetime would either trigger a Pydantic warning or be
    silently treated as UTC. Pin the contract."""
    now = _utc(2026, 5, 1, 10, 0)
    next_run = _compute_next_run("*/30 * * * *", now=now)
    assert next_run.tzinfo is not None
