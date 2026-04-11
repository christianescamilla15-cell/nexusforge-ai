"""Auto-migration runner — executes SQL migrations on startup.

Runs every *.sql file under ``backend/app/db/migrations/`` that has
not yet been recorded in the ``_migrations`` table. Each file runs
inside its own transaction; on success, the filename is inserted
into ``_migrations``.

Resilience contract (changed 2026-04-11):
  - A failing migration does NOT halt subsequent migrations. The
    failure is logged at ERROR level and added to the ``failed``
    list in the summary; the runner continues with the next file.
    Previously a single failure triggered ``break`` which silently
    blocked every later migration — that shipped a broken state to
    production (see CRITICAL_RULES / session_2026_04_11_part1.md).
  - Optional migrations (e.g. pgvector, which requires an extension
    not available on every host) are still tracked as ``skipped``
    rather than ``failed``, so their absence is expected.
  - ``/api/health`` reports the count of rows in ``_migrations`` —
    that number is NOT equivalent to "all migrations applied".
    Consumers that need to verify migration health should compare
    the set of rows in ``_migrations`` against the set of files on
    disk and alert on any non-empty diff.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Migrations that require extensions not available on all hosts
OPTIONAL_MIGRATIONS = {"006_pgvector_embeddings.sql"}


async def run_migrations(pool) -> dict:
    """Run all pending migrations in order. Returns a summary dict.

    Summary keys:
        applied:         list of filenames successfully applied this run
        skipped:         optional migrations that failed with a
                         non-fatal error (e.g. missing extension)
        failed:          migrations that raised a fatal error.
                         **The runner continues past these** so newer
                         migrations still get a chance.
        already_applied: count of rows already present in _migrations
                         at the start of this run
    """
    applied: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []

    # Ensure tracking table exists
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT now()
            )
        """)

        already_applied = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM _migrations")
        }

    migration_files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR)
        if f.endswith(".sql") and f not in already_applied
    )

    for filename in migration_files:
        sql = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO _migrations (filename) VALUES ($1)", filename
                    )
            applied.append(filename)
            logger.info("Migration applied: %s", filename)
        except Exception as exc:
            if filename in OPTIONAL_MIGRATIONS:
                skipped.append(filename)
                logger.warning(
                    "Optional migration skipped: %s — %s", filename, exc
                )
            else:
                failed.append((filename, f"{type(exc).__name__}: {exc}"))
                logger.error(
                    "Migration FAILED (continuing with next): %s — %s",
                    filename,
                    exc,
                )
                # Continue instead of break — a single broken migration
                # must not block everything downstream. Newer migrations
                # get their own transaction and may still succeed.

    summary = {
        "applied": applied,
        "skipped": skipped,
        "failed": failed,
        "already_applied": len(already_applied),
    }
    if failed:
        logger.error(
            "Migration runner finished with %d FAILED migration(s): %s",
            len(failed),
            [f for f, _ in failed],
        )
    logger.info("Migration summary: %s", summary)
    return summary
