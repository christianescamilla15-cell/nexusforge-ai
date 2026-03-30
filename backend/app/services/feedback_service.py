"""
Feedback Service — collects, stores, and aggregates operational feedback.
Enables NexusForge to learn from execution outcomes over time.
"""
from datetime import datetime
from typing import Optional
from ..models.run_feedback import RunFeedback
from ..models.agent_performance import AgentPerformance
from ..metrics.collector import collector

# In-memory storage (matches collector pattern)
_feedback_store: dict[str, RunFeedback] = {}
_performance_cache: dict[str, AgentPerformance] = {}


def submit_feedback(run_id: str, rating: int, approved: bool, comments: str = "", reviewer: str = "anonymous", feedback_type: str = "human") -> RunFeedback:
    """Submit feedback for a specific workflow run."""
    run = collector.get_run(run_id)
    workflow_name = run.workflow_name if run else "unknown"

    fb = RunFeedback(
        run_id=run_id,
        workflow_name=workflow_name,
        rating=max(1, min(5, rating)),
        approved=approved,
        feedback_type=feedback_type,
        comments=comments,
        reviewer=reviewer,
    )
    _feedback_store[fb.id] = fb

    # Auto-refresh performance after feedback
    refresh_agent_performance()

    return fb


def get_feedback_for_run(run_id: str) -> list[RunFeedback]:
    return [fb for fb in _feedback_store.values() if fb.run_id == run_id]


def get_all_feedback(limit: int = 50) -> list[RunFeedback]:
    return sorted(_feedback_store.values(), key=lambda f: f.created_at, reverse=True)[:limit]


def get_feedback_stats() -> dict:
    """Get aggregate feedback statistics."""
    all_fb = list(_feedback_store.values())
    if not all_fb:
        return {"total": 0, "avg_rating": 0, "approval_rate": 0, "by_workflow": {}}

    total = len(all_fb)
    avg_rating = sum(fb.rating for fb in all_fb) / total
    approved_count = sum(1 for fb in all_fb if fb.approved)

    by_workflow = {}
    for fb in all_fb:
        wf = fb.workflow_name
        if wf not in by_workflow:
            by_workflow[wf] = {"total": 0, "avg_rating": 0, "approved": 0, "ratings": []}
        by_workflow[wf]["total"] += 1
        by_workflow[wf]["ratings"].append(fb.rating)
        if fb.approved:
            by_workflow[wf]["approved"] += 1

    for wf, data in by_workflow.items():
        data["avg_rating"] = round(sum(data["ratings"]) / len(data["ratings"]), 2)
        data["approval_rate"] = round(data["approved"] / data["total"], 3)
        del data["ratings"]

    return {
        "total": total,
        "avg_rating": round(avg_rating, 2),
        "approval_rate": round(approved_count / total, 3),
        "by_workflow": by_workflow,
    }


def refresh_agent_performance():
    """Recompute agent performance from all runs + feedback."""
    global _performance_cache
    _performance_cache = {}

    agent_data = {}

    # Gather data from all runs and steps
    for run_id, steps in collector.steps.items():
        run = collector.get_run(run_id)
        if not run:
            continue

        # Get feedback for this run
        run_feedback = get_feedback_for_run(run_id)
        run_rating = sum(fb.rating for fb in run_feedback) / len(run_feedback) if run_feedback else 0
        run_approved = any(fb.approved for fb in run_feedback) if run_feedback else False

        for step in steps:
            name = step.agent_name
            if name not in agent_data:
                agent_data[name] = {
                    "total": 0, "success": 0, "failed": 0,
                    "latencies": [], "quality_scores": [],
                    "retried": 0, "fallbacks": 0, "approved": 0,
                }

            agent_data[name]["total"] += 1
            if step.status.value == "completed":
                agent_data[name]["success"] += 1
            elif step.status.value == "failed":
                agent_data[name]["failed"] += 1
            if step.retry_count > 0:
                agent_data[name]["retried"] += 1
            if step.latency_ms:
                agent_data[name]["latencies"].append(step.latency_ms)
            if run_rating > 0:
                agent_data[name]["quality_scores"].append(run_rating / 5.0)
            if run_approved:
                agent_data[name]["approved"] += 1

    # Count fallbacks from events
    for run_id, events in collector.events.items():
        for event in events:
            if event.event_type.value == "fallback" and event.agent_name in agent_data:
                agent_data[event.agent_name]["fallbacks"] += 1

    # Compute performance scores
    for name, data in agent_data.items():
        total = data["total"]
        if total == 0:
            continue

        success_rate = data["success"] / total
        avg_quality = sum(data["quality_scores"]) / len(data["quality_scores"]) if data["quality_scores"] else 0.5
        avg_latency = sum(data["latencies"]) / len(data["latencies"]) if data["latencies"] else 0
        retry_rate = data["retried"] / total
        fallback_rate = data["fallbacks"] / total
        approval_rate = data["approved"] / total

        # Operational score: weighted formula
        latency_efficiency = max(0, 1 - (avg_latency / 5000))  # 5s = 0 efficiency
        cost_efficiency = 0.9  # placeholder until real cost per agent tracked

        operational_score = (
            0.35 * success_rate +
            0.25 * avg_quality +
            0.15 * approval_rate +
            0.15 * latency_efficiency +
            0.10 * cost_efficiency
        )

        perf = AgentPerformance(
            agent_name=name,
            total_runs=total,
            successful_runs=data["success"],
            failed_runs=data["failed"],
            success_rate=round(success_rate, 3),
            avg_quality_score=round(avg_quality, 3),
            avg_latency_ms=round(avg_latency, 1),
            retry_rate=round(retry_rate, 3),
            fallback_rate=round(fallback_rate, 3),
            approval_rate=round(approval_rate, 3),
            operational_score=round(operational_score, 3),
        )
        _performance_cache[name] = perf


def get_agent_performance(agent_name: str = None) -> list[AgentPerformance]:
    """Get performance data, optionally filtered by agent."""
    if not _performance_cache:
        refresh_agent_performance()

    if agent_name:
        perf = _performance_cache.get(agent_name)
        return [perf] if perf else []

    return sorted(_performance_cache.values(), key=lambda p: p.operational_score, reverse=True)


def get_top_agents(n: int = 5) -> list[AgentPerformance]:
    """Get top N agents by operational score."""
    return get_agent_performance()[:n]


def get_agent_recommendations(workflow_name: str = "") -> dict:
    """Recommend best agents based on operational performance."""
    agents = get_agent_performance()
    if not agents:
        return {"status": "no_data", "recommendations": []}

    recommendations = []
    for a in agents[:10]:
        status = "excellent" if a.operational_score >= 0.8 else "good" if a.operational_score >= 0.6 else "needs_improvement"
        recommendations.append({
            "agent": a.agent_name,
            "score": a.operational_score,
            "status": status,
            "success_rate": a.success_rate,
            "avg_latency_ms": a.avg_latency_ms,
            "suggestion": f"{'Keep' if status == 'excellent' else 'Monitor' if status == 'good' else 'Review'} {a.agent_name}",
        })

    return {"status": "ok", "recommendations": recommendations, "total_agents": len(agents)}
