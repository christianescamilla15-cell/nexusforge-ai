"""Health check endpoint — reports DB, Redis, and agent status."""

import logging
from fastapi import APIRouter

from app.db.client import get_db_pool, get_redis
from app.agents.registry import list_agents

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Check DB, Redis connectivity and return agent count."""
    db_ok = False
    redis_ok = False
    agent_count = 0

    # Database check
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception as exc:
        logger.warning("Health check — DB unreachable: %s", exc)

    # Redis check
    try:
        redis = await get_redis()
        await redis.ping()
        redis_ok = True
    except Exception as exc:
        logger.warning("Health check — Redis unreachable: %s", exc)

    # Agent count
    try:
        agent_count = len(list_agents())
    except Exception:
        pass

    # Migration count
    migration_count = 0
    if db_ok:
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                migration_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM _migrations"
                )
        except Exception:
            pass

    overall = "healthy" if (db_ok and redis_ok) else "degraded"

    # Agent health scores from circuit breaker
    agent_health = {}
    try:
        from app.healing.circuit_breaker import get_circuit_breaker
        agent_health = get_circuit_breaker().get_all_health()
    except Exception:
        pass

    return {
        "status": overall,
        "service": "NexusForge AI",
        "components": {
            "database": "up" if db_ok else "down",
            "redis": "up" if redis_ok else "down",
        },
        "migrations_applied": migration_count,
        "agent_count": agent_count,
        "agent_health": agent_health,
    }
