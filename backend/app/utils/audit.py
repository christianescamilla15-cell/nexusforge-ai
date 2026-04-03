"""Audit helper — log actions to the audit_logs table."""

import json
import logging

from app.db.client import get_db_pool

logger = logging.getLogger(__name__)


async def log_audit(user_id, entity_type, entity_id, action, changes=None, ip=None):
    """Insert a row into audit_logs.

    Parameters
    ----------
    user_id : str | None   — UUID of the acting user (can be None for system actions)
    entity_type : str       — automation, workflow, agent_config, connector, rule, variable
    entity_id : str | UUID  — UUID of the affected entity
    action : str            — created, updated, deleted, executed, published
    changes : dict | None   — JSON-serialisable diff (old → new)
    ip : str | None         — client IP address
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO audit_logs
                       (user_id, entity_type, entity_id, action, changes, ip_address)
                   VALUES ($1::uuid, $2, $3::uuid, $4, $5::jsonb, $6)""",
                user_id,
                entity_type,
                str(entity_id),
                action,
                json.dumps(changes or {}),
                ip,
            )
    except Exception:
        logger.exception("Failed to write audit log")
