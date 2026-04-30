"""Health check endpoint — reports DB, Redis, and agent status."""

import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

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
        agent_health = await get_circuit_breaker().get_all_health()
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


@router.get("/health/ready")
async def readiness_probe():
    """Readiness probe — 200 only if every required dependency is up.

    Tier 4 verification (2026-04-30 triangulation): docs/DEPLOYMENT.md
    documented this path but the route didn't exist. K8s/Render
    readiness probes pointed at it would have flagged the pod as
    NotReady on every poll regardless of actual state.

    Distinct from `/api/health` (which always returns 200 with a
    body describing degradation) and `/api/ping` (which doesn't
    touch DB or Redis at all). Use this one for orchestrators that
    decide pod traffic eligibility on HTTP status code alone.
    """
    db_ok = False
    redis_ok = False
    redis_error = None

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception as exc:
        logger.warning("Readiness — DB unreachable: %s", exc)

    try:
        redis = await get_redis()
        await redis.ping()
        redis_ok = True
    except Exception as exc:
        redis_error = f"{type(exc).__name__}: {exc}"
        logger.warning("Readiness — Redis unreachable: %s", redis_error)

    body = {
        "ready": db_ok and redis_ok,
        "components": {
            "database": "up" if db_ok else "down",
            "redis": "up" if redis_ok else ("down: " + (redis_error or "unknown")),
        },
    }
    status_code = 200 if (db_ok and redis_ok) else 503
    return JSONResponse(content=body, status_code=status_code)
