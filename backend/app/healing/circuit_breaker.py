"""Per-agent circuit breaker with Redis-backed shared state.

State is stored in Redis so it's shared across all Uvicorn workers.
Falls back to in-memory if Redis is unavailable.
"""

import json
import logging
import time

logger = logging.getLogger(__name__)

_FAILURE_THRESHOLD = 3
_RECOVERY_TIMEOUT = 30
_HEALTH_ALPHA = 0.3
_LATENCY_PENALTY_MS = 5000
_REDIS_PREFIX = "nxf:cb:"
_REDIS_TTL = 300  # 5 min TTL per key


async def _get_redis():
    """Get Redis connection (best-effort)."""
    try:
        from app.db.client import get_redis
        return await get_redis()
    except Exception:
        return None


async def _read_state(redis, agent_name: str) -> dict:
    """Read agent state from Redis."""
    try:
        data = await redis.get(f"{_REDIS_PREFIX}{agent_name}")
        if data:
            return json.loads(data)
    except Exception:
        pass
    return {
        "health_score": 1.0,
        "consecutive_failures": 0,
        "total_successes": 0,
        "total_failures": 0,
        "circuit_open_until": 0,
        "last_error": "",
    }


async def _write_state(redis, agent_name: str, state: dict):
    """Write agent state to Redis with TTL."""
    try:
        await redis.setex(
            f"{_REDIS_PREFIX}{agent_name}",
            _REDIS_TTL,
            json.dumps(state),
        )
    except Exception:
        pass


class AgentCircuitBreaker:
    """Manages circuit breakers and health scores for all agents.
    Uses Redis for shared state across workers. Falls back to in-memory."""

    def __init__(self):
        self._local: dict[str, dict] = {}  # fallback if Redis unavailable

    def _local_state(self, agent_name: str) -> dict:
        if agent_name not in self._local:
            self._local[agent_name] = {
                "health_score": 1.0, "consecutive_failures": 0,
                "total_successes": 0, "total_failures": 0,
                "circuit_open_until": 0, "last_error": "",
            }
        return self._local[agent_name]

    async def is_available(self, agent_name: str) -> bool:
        """Check if agent circuit is closed (available)."""
        redis = await _get_redis()
        if redis:
            state = await _read_state(redis, agent_name)
        else:
            state = self._local_state(agent_name)

        if state["circuit_open_until"] > time.time():
            logger.info("Circuit open for '%s', skipping", agent_name)
            return False
        return True

    async def record_success(self, agent_name: str, latency_ms: float = 0):
        """Record successful execution."""
        redis = await _get_redis()
        if redis:
            state = await _read_state(redis, agent_name)
        else:
            state = self._local_state(agent_name)

        state["consecutive_failures"] = 0
        state["total_successes"] += 1

        latency_penalty = min(latency_ms / _LATENCY_PENALTY_MS, 0.5)
        new_score = 1.0 - latency_penalty
        state["health_score"] = _HEALTH_ALPHA * new_score + (1 - _HEALTH_ALPHA) * state["health_score"]
        state["health_score"] = max(0.0, min(1.0, state["health_score"]))

        if redis:
            await _write_state(redis, agent_name, state)

    async def record_failure(self, agent_name: str, error: str = ""):
        """Record failure. May open circuit."""
        redis = await _get_redis()
        if redis:
            state = await _read_state(redis, agent_name)
        else:
            state = self._local_state(agent_name)

        state["consecutive_failures"] += 1
        state["total_failures"] += 1
        state["last_error"] = error[:200]
        state["health_score"] = _HEALTH_ALPHA * 0.0 + (1 - _HEALTH_ALPHA) * state["health_score"]
        state["health_score"] = max(0.0, state["health_score"])

        if state["consecutive_failures"] >= _FAILURE_THRESHOLD:
            state["circuit_open_until"] = time.time() + _RECOVERY_TIMEOUT
            logger.warning(
                "Circuit breaker OPEN for '%s' (failures=%d, health=%.2f) — cooldown %ds",
                agent_name, state["consecutive_failures"], state["health_score"], _RECOVERY_TIMEOUT,
            )

        if redis:
            await _write_state(redis, agent_name, state)

    def get_health(self, agent_name: str) -> float:
        """Get health score (sync, from local cache only)."""
        state = self._local.get(agent_name, {})
        return state.get("health_score", 1.0)

    async def get_all_health(self) -> dict[str, dict]:
        """Get health for all tracked agents."""
        redis = await _get_redis()
        if redis:
            try:
                keys = []
                async for key in redis.scan_iter(f"{_REDIS_PREFIX}*"):
                    keys.append(key)
                result = {}
                for key in keys:
                    name = key.replace(_REDIS_PREFIX, "") if isinstance(key, str) else key.decode().replace(_REDIS_PREFIX, "")
                    state = await _read_state(redis, name)
                    result[name] = {
                        "health_score": round(state["health_score"], 3),
                        "circuit_open": state["circuit_open_until"] > time.time(),
                        "consecutive_failures": state["consecutive_failures"],
                        "total_successes": state["total_successes"],
                        "total_failures": state["total_failures"],
                        "last_error": state["last_error"],
                    }
                return result
            except Exception:
                pass

        # Fallback to local
        return {
            name: {
                "health_score": round(s.get("health_score", 1.0), 3),
                "circuit_open": s.get("circuit_open_until", 0) > time.time(),
                "consecutive_failures": s.get("consecutive_failures", 0),
                "total_successes": s.get("total_successes", 0),
                "total_failures": s.get("total_failures", 0),
                "last_error": s.get("last_error", ""),
            }
            for name, s in self._local.items()
        }


_breaker: AgentCircuitBreaker | None = None


def get_circuit_breaker() -> AgentCircuitBreaker:
    global _breaker
    if _breaker is None:
        _breaker = AgentCircuitBreaker()
    return _breaker
