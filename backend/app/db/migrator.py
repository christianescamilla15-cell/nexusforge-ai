"""Auto-migration runner — executes SQL migrations on startup."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Migrations that require extensions not available on all hosts
OPTIONAL_MIGRATIONS = {"006_pgvector_embeddings.sql"}


async def run_migrations(pool) -> dict:
    """Run all pending migrations in order. Returns summary."""
    applied = []
    skipped = []
    failed = []

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
                logger.warning("Optional migration skipped: %s — %s", filename, exc)
            else:
                failed.append(filename)
                logger.error("Migration FAILED: %s — %s", filename, exc)
                break  # Stop on failure

    summary = {
        "applied": applied,
        "skipped": skipped,
        "failed": failed,
        "already_applied": len(already_applied),
    }
    logger.info("Migration summary: %s", summary)
    return summary
