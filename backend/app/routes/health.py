"""Health check endpoint — reports DB, Redis, and agent status."""

import logging
from fastapi import APIRouter

from app.db.client import get_db_pool, get_redis
from app.agents.registry import list_agents

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/ping")
async def ping():
    """Lightweight ping for uptime monitors. No DB, instant."""
    return {"pong": True}


@router.get("/version")
async def version():
    """Build info and version."""
    return {
        "version": "2.5.0",
        "agents": 24,
        "topologies": 6,
        "integrations": 8,
        "modules": 108,
        "components": 43,
    }


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
    redis_error = None
    try:
        redis = await get_redis()
        await redis.ping()
        redis_ok = True
    except Exception as exc:
        redis_error = f"{type(exc).__name__}: {exc}"
        logger.warning("Health check — Redis unreachable: %s", redis_error)

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
            "redis": "up" if redis_ok else ("down: " + (redis_error or "unknown")),
        },
        "migrations_applied": migration_count,
        "agent_count": agent_count,
        "agent_health": agent_health,
    }
