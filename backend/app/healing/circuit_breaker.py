"""Per-agent circuit breaker with adaptive health scoring.

Prevents hammering a failing agent/provider and tracks health over time
using an exponential moving average.
"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Defaults
_FAILURE_THRESHOLD = 3       # consecutive failures to open the circuit
_RECOVERY_TIMEOUT = 30       # seconds before half-open probe
_HEALTH_ALPHA = 0.3          # EMA smoothing factor (higher = more reactive)
_LATENCY_PENALTY_MS = 5000   # latency beyond this penalizes health


@dataclass
class AgentHealthRecord:
    """Tracks health for a single agent."""
    agent_name: str
    health_score: float = 1.0       # 0.0 = dead, 1.0 = perfect
    consecutive_failures: int = 0
    total_successes: int = 0
    total_failures: int = 0
    circuit_open_until: float = 0.0  # monotonic timestamp
    last_error: str = ""
    last_success_time: float = field(default_factory=time.monotonic)

    @property
    def is_circuit_open(self) -> bool:
        return time.monotonic() < self.circuit_open_until

    @property
    def success_rate(self) -> float:
        total = self.total_successes + self.total_failures
        return self.total_successes / total if total > 0 else 1.0


class AgentCircuitBreaker:
    """Manages circuit breakers and health scores for all agents."""

    def __init__(
        self,
        failure_threshold: int = _FAILURE_THRESHOLD,
        recovery_timeout: int = _RECOVERY_TIMEOUT,
    ):
        self._threshold = failure_threshold
        self._recovery = recovery_timeout
        self._agents: dict[str, AgentHealthRecord] = {}

    def _get_record(self, agent_name: str) -> AgentHealthRecord:
        if agent_name not in self._agents:
            self._agents[agent_name] = AgentHealthRecord(agent_name=agent_name)
        return self._agents[agent_name]

    def is_available(self, agent_name: str) -> bool:
        """Check if agent is available (circuit not open)."""
        record = self._get_record(agent_name)
        if record.is_circuit_open:
            logger.info("Circuit open for '%s', skipping (reopens in %.0fs)",
                        agent_name, record.circuit_open_until - time.monotonic())
            return False
        return True

    def record_success(self, agent_name: str, latency_ms: float = 0):
        """Record a successful execution. Resets failure counter, updates health."""
        record = self._get_record(agent_name)
        record.consecutive_failures = 0
        record.total_successes += 1
        record.last_success_time = time.monotonic()

        # EMA health update with latency penalty
        latency_penalty = min(latency_ms / _LATENCY_PENALTY_MS, 0.5)
        new_score = 1.0 - latency_penalty
        record.health_score = _HEALTH_ALPHA * new_score + (1 - _HEALTH_ALPHA) * record.health_score
        record.health_score = max(0.0, min(1.0, record.health_score))

    def record_failure(self, agent_name: str, error: str = ""):
        """Record a failure. May open the circuit."""
        record = self._get_record(agent_name)
        record.consecutive_failures += 1
        record.total_failures += 1
        record.last_error = error[:200]

        # EMA health update
        record.health_score = _HEALTH_ALPHA * 0.0 + (1 - _HEALTH_ALPHA) * record.health_score
        record.health_score = max(0.0, record.health_score)

        # Trip circuit if threshold reached
        if record.consecutive_failures >= self._threshold:
            record.circuit_open_until = time.monotonic() + self._recovery
            logger.warning(
                "Circuit breaker OPEN for '%s' (failures=%d, health=%.2f) — cooldown %ds",
                agent_name, record.consecutive_failures, record.health_score, self._recovery,
            )

    def get_health(self, agent_name: str) -> float:
        """Get current health score for an agent (0.0-1.0)."""
        return self._get_record(agent_name).health_score

    def get_all_health(self) -> dict[str, dict]:
        """Get health status for all tracked agents."""
        return {
            name: {
                "health_score": round(r.health_score, 3),
                "success_rate": round(r.success_rate, 3),
                "circuit_open": r.is_circuit_open,
                "consecutive_failures": r.consecutive_failures,
                "total_successes": r.total_successes,
                "total_failures": r.total_failures,
                "last_error": r.last_error,
            }
            for name, r in self._agents.items()
        }


# Module-level singleton
_breaker: AgentCircuitBreaker | None = None


def get_circuit_breaker() -> AgentCircuitBreaker:
    global _breaker
    if _breaker is None:
        _breaker = AgentCircuitBreaker()
    return _breaker
