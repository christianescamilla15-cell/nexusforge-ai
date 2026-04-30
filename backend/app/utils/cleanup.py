"""Shared cleanup helpers — single source of truth for jobs that ran
in two places before consolidation.

2026-04-30 (Tier 5 #1): the zombie-run cleanup logic was duplicated
across `main.py:_zombie_cleanup_loop` (background task, fires every
5 minutes) and `routes/executions.py:cleanup_zombie_runs` (admin
endpoint, manual trigger). The two diverged over time:

  - main.py        WHERE status IN ('pending', 'running')
  - executions.py  WHERE status IN ('pending', 'queued', 'running')

The endpoint version (incl. `queued`) was the correct superset —
the background loop missed every queued workflow that timed out
before transitioning to running. Both call sites now share this
helper, so the SQL can't drift again.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def mark_stale_runs_as_zombies(
    pool=None,
    stale_after_minutes: int = 10,
) -> int:
    """Mark every stuck workflow_run (pending / queued / running for
    more than `stale_after_minutes`) as failed.

    Returns the number of rows updated. Both the background sweeper
    and the admin endpoint call this.

    `pool` is optional. When omitted, the function calls
    `get_db_pool()` lazily so this module does NOT add an import
    cycle on `app.db.client` at import time.

    Errors are propagated. Callers handle them according to context:
      - the background loop logs at DEBUG and keeps running.
      - the HTTP endpoint returns a 500.
    """
    if pool is None:
        from app.db.client import get_db_pool
        pool = await get_db_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE workflow_runs
                   SET status = 'failed',
                       completed_at = now(),
                       error_message = 'Execution timed out (zombie cleanup)'
                 WHERE status IN ('pending', 'queued', 'running')
                   AND created_at < now() - make_interval(mins => $1)""",
            stale_after_minutes,
        )

    if result and result != "UPDATE 0":
        try:
            count = int(result.split()[-1])
        except (ValueError, IndexError):
            count = 0
    else:
        count = 0
    if count:
        logger.info("Zombie cleanup: marked %d stale run(s) as failed", count)
    return count
