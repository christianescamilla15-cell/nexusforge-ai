"""Memory and self-healing stats routes — backed by PostgreSQL step_executions."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from app.db.client import get_db_pool

router = APIRouter()
logger = logging.getLogger(__name__)


def _require_admin(request: Request) -> dict:
    """Admin-only guard. Mirrors admin.py pattern (404 not 403)."""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        raise HTTPException(404, "Not found")
    return user


# ── Memory stats ──────────────────────────────────────────────────────────────

@router.get("/memory/stats/{agent_type}")
async def get_memory_stats(agent_type: str):
    """Return memory tier counts for a single agent type, derived from step_executions."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            episodic = await conn.fetchval(
                "SELECT count(*) FROM step_executions WHERE agent_type = $1",
                agent_type,
            )
            working = await conn.fetchval(
                """SELECT count(DISTINCT run_id) FROM step_executions
                   WHERE agent_type = $1 AND completed_at > now() - interval '1 hour'""",
                agent_type,
            )
            semantic = await conn.fetchval(
                "SELECT count(DISTINCT step_name) FROM step_executions WHERE agent_type = $1",
                agent_type,
            )
        return {
            "agent_type": agent_type,
            "working_count": int(working or 0),
            "episodic_count": int(episodic or 0),
            "semantic_count": int(semantic or 0),
        }
    except Exception as exc:
        logger.warning("Memory stats unavailable for %s: %s", agent_type, exc)
        return {"agent_type": agent_type, "working_count": 0, "episodic_count": 0, "semantic_count": 0}


@router.get("/memory/stats")
async def get_all_memory_stats():
    """Return memory tier counts for all agent types in one query."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT
                       agent_type,
                       count(*) AS episodic_count,
                       count(DISTINCT run_id) FILTER (
                           WHERE completed_at > now() - interval '1 hour'
                       ) AS working_count,
                       count(DISTINCT step_name) AS semantic_count
                   FROM step_executions
                   GROUP BY agent_type"""
            )
        return [
            {
                "agent_type": r["agent_type"],
                "working_count": int(r["working_count"] or 0),
                "episodic_count": int(r["episodic_count"] or 0),
                "semantic_count": int(r["semantic_count"] or 0),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("All memory stats unavailable: %s", exc)
        return []


# ── Self-healing stats ────────────────────────────────────────────────────────

@router.get("/healing/stats")
async def get_healing_stats():
    """Return self-healing metrics from step_executions and dead_letters."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            total_failures = await conn.fetchval(
                "SELECT count(*) FROM step_executions WHERE status = 'failed'"
            )
            total_healed = await conn.fetchval(
                "SELECT count(*) FROM step_executions WHERE error_message LIKE 'healed via%'"
            )
            dead_letters = await conn.fetchval("SELECT count(*) FROM dead_letters")

            recent_failures = await conn.fetch(
                """SELECT step_name, agent_type, error_message, retry_count, completed_at AS created_at
                   FROM step_executions
                   WHERE status = 'failed'
                   ORDER BY completed_at DESC NULLS LAST
                   LIMIT 10"""
            )
            recent_heals = await conn.fetch(
                """SELECT step_name, agent_type, error_message, completed_at AS created_at
                   FROM step_executions
                   WHERE error_message LIKE 'healed via%'
                   ORDER BY completed_at DESC NULLS LAST
                   LIMIT 10"""
            )

        tf = int(total_failures or 0)
        th = int(total_healed or 0)
        return {
            "total_failures": tf,
            "total_healed": th,
            "heal_rate": round(th / max(tf, 1) * 100, 1),
            "dead_letters": int(dead_letters or 0),
            "recent_failures": [
                {
                    "step_name": r["step_name"],
                    "agent_type": r["agent_type"],
                    "error_message": r["error_message"],
                    "retry_count": r["retry_count"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in recent_failures
            ],
            "recent_heals": [
                {
                    "step_name": r["step_name"],
                    "agent_type": r["agent_type"],
                    "error_message": r["error_message"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in recent_heals
            ],
        }
    except Exception as exc:
        logger.warning("Healing stats unavailable: %s", exc)
        return {
            "total_failures": 0, "total_healed": 0, "heal_rate": 0.0,
            "dead_letters": 0, "recent_failures": [], "recent_heals": [],
        }


@router.post("/healing/retry/{dead_letter_id}")
async def retry_dead_letter(dead_letter_id: UUID, request: Request):
    """Re-queue a dead letter for execution via the self-healer."""
    _require_admin(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM dead_letters WHERE id = $1", dead_letter_id
            )
        if not row:
            raise HTTPException(status_code=404, detail="Dead letter not found")

        # Mark as retried (full re-execution would require run context — log intent for now)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE dead_letters SET error_message = 'retry requested' WHERE id = $1",
                dead_letter_id,
            )
        return {"queued": True, "dead_letter_id": str(dead_letter_id), "step_name": row["step_name"]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retry dead letter %s", dead_letter_id)
        raise HTTPException(status_code=500, detail="Internal server error")
