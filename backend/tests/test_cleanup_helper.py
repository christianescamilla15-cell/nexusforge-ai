"""Tests for `app.utils.cleanup.mark_stale_runs_as_zombies`.

T5 #1 from 2026-04-30. The helper consolidates the two
divergent implementations that previously lived in main.py
(background loop) and routes/executions.py (admin endpoint).

We don't have a live DB in these tests — instead we verify the
helper's SQL contract using a tiny fake asyncpg pool. What we
care about:

  1. The status filter includes ALL THREE of ('pending', 'queued',
     'running') — the old main.py background loop missed 'queued'.
  2. The threshold is parametrized; default is 10 minutes.
  3. Return value is the row count parsed from asyncpg's
     "UPDATE N" status string.
  4. "UPDATE 0" → returns 0.
"""
from __future__ import annotations

import pytest

from app.utils.cleanup import mark_stale_runs_as_zombies


# ─── fake pool ───────────────────────────────────────────────────────


class _FakeConn:
    def __init__(self, return_value: str):
        self._return_value = return_value
        self.last_query: str | None = None
        self.last_args: tuple = ()

    async def execute(self, query: str, *args):
        self.last_query = query
        self.last_args = args
        return self._return_value


class _FakeAcquireCtx:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *_):
        return False


class _FakePool:
    def __init__(self, return_value: str):
        self.conn = _FakeConn(return_value)

    def acquire(self):
        return _FakeAcquireCtx(self.conn)


# ─── tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_includes_pending_queued_and_running_in_status_filter():
    """The new helper must filter all three statuses. The old
    main.py loop only filtered ('pending', 'running') and missed
    queued runs that timed out before transitioning."""
    pool = _FakePool("UPDATE 3")
    await mark_stale_runs_as_zombies(pool=pool)

    sql = pool.conn.last_query
    assert "'pending'" in sql
    assert "'queued'" in sql
    assert "'running'" in sql


@pytest.mark.asyncio
async def test_default_threshold_is_ten_minutes():
    pool = _FakePool("UPDATE 0")
    await mark_stale_runs_as_zombies(pool=pool)
    assert pool.conn.last_args == (10,)


@pytest.mark.asyncio
async def test_custom_threshold_passed_through():
    pool = _FakePool("UPDATE 0")
    await mark_stale_runs_as_zombies(pool=pool, stale_after_minutes=30)
    assert pool.conn.last_args == (30,)


@pytest.mark.asyncio
async def test_returns_parsed_row_count():
    pool = _FakePool("UPDATE 7")
    count = await mark_stale_runs_as_zombies(pool=pool)
    assert count == 7


@pytest.mark.asyncio
async def test_update_zero_returns_zero():
    pool = _FakePool("UPDATE 0")
    count = await mark_stale_runs_as_zombies(pool=pool)
    assert count == 0


@pytest.mark.asyncio
async def test_unparseable_result_returns_zero():
    """Defensive: if asyncpg ever returns something unexpected, the
    helper returns 0 instead of crashing the scheduler loop."""
    pool = _FakePool("WHATEVER")
    count = await mark_stale_runs_as_zombies(pool=pool)
    assert count == 0


@pytest.mark.asyncio
async def test_sql_uses_make_interval_with_parameter():
    """Pin that the threshold is bound as a SQL parameter, not
    string-interpolated. Prevents future SQL-injection regressions
    if the threshold ever becomes user-supplied."""
    pool = _FakePool("UPDATE 0")
    await mark_stale_runs_as_zombies(pool=pool, stale_after_minutes=15)
    sql = pool.conn.last_query
    assert "make_interval(mins => $1)" in sql
    assert pool.conn.last_args == (15,)
