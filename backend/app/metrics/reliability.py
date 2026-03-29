"""
Agent Reliability System — measures agent performance across runs.

Tracks:
- Success rate per agent
- Average latency per agent
- Failure patterns
- Cost efficiency
- Retry frequency
"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from .collector import collector


@dataclass
class AgentReliabilityScore:
    agent_name: str
    total_executions: int = 0
    successful: int = 0
    failed: int = 0
    retried: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    avg_cost_per_run: float = 0.0
    retry_rate: float = 0.0
    fallback_count: int = 0
    common_errors: list = field(default_factory=list)


def compute_agent_reliability() -> list[AgentReliabilityScore]:
    """Compute reliability scores for all agents across all runs."""
    agent_data = defaultdict(lambda: {
        "executions": 0, "success": 0, "failed": 0, "retried": 0,
        "latencies": [], "costs": [], "errors": [], "fallbacks": 0,
    })

    for run_id, steps in collector.steps.items():
        for step in steps:
            name = step.agent_name
            agent_data[name]["executions"] += 1

            if step.status.value == "completed":
                agent_data[name]["success"] += 1
            elif step.status.value == "failed":
                agent_data[name]["failed"] += 1
                if step.error_message:
                    agent_data[name]["errors"].append(step.error_message)

            if step.retry_count > 0:
                agent_data[name]["retried"] += 1

            if step.latency_ms:
                agent_data[name]["latencies"].append(step.latency_ms)

    # Count fallbacks from events
    for run_id, events in collector.events.items():
        for event in events:
            if event.event_type.value == "fallback":
                agent_data[event.agent_name]["fallbacks"] += 1

    scores = []
    for name, data in sorted(agent_data.items()):
        total = data["executions"]
        score = AgentReliabilityScore(
            agent_name=name,
            total_executions=total,
            successful=data["success"],
            failed=data["failed"],
            retried=data["retried"],
            success_rate=data["success"] / max(total, 1),
            avg_latency_ms=sum(data["latencies"]) / max(len(data["latencies"]), 1),
            retry_rate=data["retried"] / max(total, 1),
            fallback_count=data["fallbacks"],
            common_errors=list(set(data["errors"]))[:5],  # top 5 unique errors
        )
        scores.append(score)

    return scores


def get_system_health() -> dict:
    """Get overall system health summary."""
    scores = compute_agent_reliability()
    total_runs = len(collector.runs)
    successful_runs = sum(1 for r in collector.runs.values() if r.status.value == "completed")

    return {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": total_runs - successful_runs,
        "system_success_rate": successful_runs / max(total_runs, 1),
        "total_agents_tracked": len(scores),
        "agents": [
            {
                "agent": s.agent_name,
                "executions": s.total_executions,
                "success_rate": round(s.success_rate, 3),
                "avg_latency_ms": round(s.avg_latency_ms, 1),
                "retry_rate": round(s.retry_rate, 3),
                "fallbacks": s.fallback_count,
            }
            for s in scores
        ],
    }
