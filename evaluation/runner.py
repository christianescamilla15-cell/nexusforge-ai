"""
Evaluation runner for NexusForge AI.

Executes defined scenarios against the orchestration engine
and produces evaluation metrics and reports.

Usage:
    python -m evaluation.runner
    python -m evaluation.runner --scenario research_task
"""
import json
import os
import time
from pathlib import Path
from typing import List, Optional
from .metrics.metrics import ScenarioResult, EvaluationReport


SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def load_scenarios(scenario_name: Optional[str] = None) -> List[dict]:
    """Load evaluation scenarios from JSON files."""
    scenarios = []
    for f in SCENARIOS_DIR.glob("*.json"):
        if scenario_name and f.stem != scenario_name:
            continue
        with open(f) as fp:
            scenario = json.load(fp)
            scenario["_file"] = f.stem
            scenarios.append(scenario)
    return scenarios


def evaluate_output(output: dict, scenario: dict) -> float:
    """
    Score output quality against scenario expectations.
    Returns a score between 0.0 and 1.0.
    """
    score = 0.0
    criteria = scenario.get("success_criteria", {})

    # Check required content
    must_contain = criteria.get("output_must_contain", [])
    output_text = json.dumps(output).lower()
    if must_contain:
        matches = sum(1 for term in must_contain if term.lower() in output_text)
        score += (matches / len(must_contain)) * 0.5

    # Check agent count
    min_agents = criteria.get("min_agents_used", 0)
    agents_used = output.get("agents_used", 0)
    if agents_used >= min_agents:
        score += 0.25

    # Check completion
    if output.get("status") == "completed":
        score += 0.25

    return min(score, 1.0)


def run_scenario(scenario: dict) -> ScenarioResult:
    """
    Execute a single evaluation scenario.

    In production, this would call the orchestrator API.
    For now, it simulates execution for metric collection.
    """
    start = time.time()

    try:
        # Simulate workflow execution
        # TODO: Replace with actual API call to POST /api/workflows/execute
        simulated_output = {
            "status": "completed",
            "agents_used": len(scenario.get("expected_agents", [])),
            "output": f"Simulated output for scenario: {scenario['name']}",
            "retries": 0,
            "fallback": False,
        }

        latency = (time.time() - start) * 1000
        quality = evaluate_output(simulated_output, scenario)

        return ScenarioResult(
            scenario_name=scenario["name"],
            success=True,
            latency_ms=latency,
            agents_used=simulated_output["agents_used"],
            retry_count=simulated_output["retries"],
            fallback_triggered=simulated_output["fallback"],
            output_quality_score=quality,
        )

    except Exception as e:
        latency = (time.time() - start) * 1000
        return ScenarioResult(
            scenario_name=scenario["name"],
            success=False,
            latency_ms=latency,
            agents_used=0,
            retry_count=0,
            fallback_triggered=False,
            output_quality_score=0.0,
            error=str(e),
        )


def run_evaluation(scenario_name: Optional[str] = None) -> EvaluationReport:
    """Run all evaluation scenarios and produce a report."""
    scenarios = load_scenarios(scenario_name)
    results = []

    for scenario in scenarios:
        print(f"Running scenario: {scenario['name']}...")
        result = run_scenario(scenario)
        results.append(result)
        status = "PASS" if result.success else "FAIL"
        print(f"  {status} — {result.latency_ms:.0f}ms — quality: {result.output_quality_score:.2f}")

    report = EvaluationReport()
    report.compute(results)

    print(f"\n{'='*50}")
    print(f"Evaluation Complete")
    print(f"  Scenarios: {report.total_scenarios}")
    print(f"  Passed: {report.passed}")
    print(f"  Failed: {report.failed}")
    print(f"  Success Rate: {report.task_success_rate:.1%}")
    print(f"  Avg Latency: {report.average_latency_ms:.0f}ms")
    print(f"  Avg Quality: {report.average_quality_score:.2f}")
    print(f"{'='*50}")

    return report


if __name__ == "__main__":
    import sys
    scenario = sys.argv[1] if len(sys.argv) > 1 else None
    run_evaluation(scenario)
