"""
Evaluation metrics for NexusForge AI workflow assessment.

Measures task success, latency, cost efficiency, and recovery behavior
across defined evaluation scenarios.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class ScenarioResult:
    """Result of a single scenario evaluation."""
    scenario_name: str
    success: bool
    latency_ms: float
    agents_used: int
    retry_count: int
    fallback_triggered: bool
    output_quality_score: float  # 0.0 to 1.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class EvaluationReport:
    """Aggregated evaluation report across all scenarios."""
    total_scenarios: int = 0
    passed: int = 0
    failed: int = 0
    task_success_rate: float = 0.0
    average_latency_ms: float = 0.0
    total_cost: float = 0.0
    cost_per_run: float = 0.0
    average_retry_count: float = 0.0
    fallback_rate: float = 0.0
    average_quality_score: float = 0.0
    results: List[ScenarioResult] = field(default_factory=list)

    def compute(self, results: List[ScenarioResult]):
        """Compute aggregate metrics from scenario results."""
        self.results = results
        self.total_scenarios = len(results)
        self.passed = sum(1 for r in results if r.success)
        self.failed = self.total_scenarios - self.passed
        self.task_success_rate = self.passed / max(self.total_scenarios, 1)
        self.average_latency_ms = sum(r.latency_ms for r in results) / max(self.total_scenarios, 1)
        self.average_retry_count = sum(r.retry_count for r in results) / max(self.total_scenarios, 1)
        self.fallback_rate = sum(1 for r in results if r.fallback_triggered) / max(self.total_scenarios, 1)
        self.average_quality_score = sum(r.output_quality_score for r in results) / max(self.total_scenarios, 1)

    def summary(self) -> dict:
        """Return a summary dict for API responses."""
        return {
            "total_scenarios": self.total_scenarios,
            "passed": self.passed,
            "failed": self.failed,
            "task_success_rate": round(self.task_success_rate, 3),
            "average_latency_ms": round(self.average_latency_ms, 1),
            "average_retry_count": round(self.average_retry_count, 2),
            "fallback_rate": round(self.fallback_rate, 3),
            "average_quality_score": round(self.average_quality_score, 3),
        }
```
