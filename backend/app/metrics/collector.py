"""
Metrics collector for workflow execution tracking.
Stores run data in-memory with optional persistence.
"""
from datetime import datetime
from typing import Dict, List, Optional
from ..models.workflow_run import WorkflowRun, RunStatus
from ..models.workflow_step import WorkflowStep, StepStatus
from ..models.agent_event import AgentEvent, EventType
from ..models.run_metrics import RunMetrics


class MetricsCollector:
    def __init__(self):
        self.runs: Dict[str, WorkflowRun] = {}
        self.steps: Dict[str, List[WorkflowStep]] = {}
        self.events: Dict[str, List[AgentEvent]] = {}

    def start_run(self, workflow_name: str, topology: str = "sequential") -> WorkflowRun:
        run = WorkflowRun(workflow_name=workflow_name, topology=topology, status=RunStatus.RUNNING)
        self.runs[run.id] = run
        self.steps[run.id] = []
        self.events[run.id] = []
        self._log_event(run.id, EventType.WORKFLOW_START, f"Workflow '{workflow_name}' started with topology '{topology}'")
        return run

    def start_step(self, run_id: str, agent_name: str, step_index: int) -> WorkflowStep:
        step = WorkflowStep(run_id=run_id, agent_name=agent_name, step_index=step_index, status=StepStatus.RUNNING)
        self.steps.setdefault(run_id, []).append(step)
        self._log_event(run_id, EventType.AGENT_START, f"Agent '{agent_name}' started (step {step_index})", agent_name)
        return step

    def end_step(self, step: WorkflowStep, provider: str = "", output_summary: str = "", tokens: int = 0, cost: float = 0.0):
        step.end_time = datetime.utcnow()
        step.latency_ms = (step.end_time - step.start_time).total_seconds() * 1000
        step.status = StepStatus.COMPLETED
        step.provider_used = provider
        step.output_summary = output_summary
        self._log_event(step.run_id, EventType.AGENT_END, f"Agent '{step.agent_name}' completed in {step.latency_ms:.0f}ms", step.agent_name)
        # Accumulate tokens/cost on the run
        run = self.runs.get(step.run_id)
        if run and tokens > 0:
            run.total_tokens = getattr(run, 'total_tokens', 0) + tokens
            run.total_cost = (run.total_cost or 0) + cost
            if provider:
                run.provider_used = provider

    def fail_step(self, step: WorkflowStep, error: str):
        step.end_time = datetime.utcnow()
        step.latency_ms = (step.end_time - step.start_time).total_seconds() * 1000
        step.status = StepStatus.FAILED
        step.error_message = error
        self._log_event(step.run_id, EventType.AGENT_FAILURE, f"Agent '{step.agent_name}' failed: {error}", step.agent_name)

    def log_retry(self, run_id: str, agent_name: str, attempt: int):
        self._log_event(run_id, EventType.RETRY, f"Agent '{agent_name}' retry attempt {attempt}", agent_name)

    def log_fallback(self, run_id: str, agent_name: str, from_provider: str, to_provider: str):
        self._log_event(run_id, EventType.FALLBACK, f"Fallback: {from_provider} → {to_provider} for agent '{agent_name}'", agent_name)

    def end_run(self, run_id: str, status: RunStatus = RunStatus.COMPLETED):
        run = self.runs.get(run_id)
        if not run:
            return
        run.end_time = datetime.utcnow()
        run.total_latency_ms = (run.end_time - run.start_time).total_seconds() * 1000
        run.status = status
        steps = self.steps.get(run_id, [])
        run.step_count = len(steps)
        run.agent_count = len(set(s.agent_name for s in steps))
        run.retry_count = sum(s.retry_count for s in steps)
        run.fallback_used = any(e.event_type == EventType.FALLBACK for e in self.events.get(run_id, []))
        self._log_event(run_id, EventType.WORKFLOW_END, f"Workflow completed with status '{status.value}' in {run.total_latency_ms:.0f}ms")

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        return self.runs.get(run_id)

    def get_runs(self, limit: int = 50) -> List[WorkflowRun]:
        return sorted(self.runs.values(), key=lambda r: r.start_time, reverse=True)[:limit]

    def get_steps(self, run_id: str) -> List[WorkflowStep]:
        return self.steps.get(run_id, [])

    def get_events(self, run_id: str) -> List[AgentEvent]:
        return self.events.get(run_id, [])

    def get_metrics(self, run_id: str) -> Optional[RunMetrics]:
        run = self.runs.get(run_id)
        if not run:
            return None
        steps = self.steps.get(run_id, [])
        events = self.events.get(run_id, [])
        completed = [s for s in steps if s.status == StepStatus.COMPLETED]
        return RunMetrics(
            run_id=run_id,
            total_latency_ms=run.total_latency_ms or 0,
            avg_step_latency_ms=sum(s.latency_ms or 0 for s in completed) / max(len(completed), 1),
            total_cost=run.total_cost,
            retry_count=sum(s.retry_count for s in steps),
            fallback_count=sum(1 for e in events if e.event_type == EventType.FALLBACK),
            success_rate=len(completed) / max(len(steps), 1),
            agents_used=len(set(s.agent_name for s in steps)),
            topology=run.topology,
        )

    def _log_event(self, run_id: str, event_type: EventType, message: str, agent_name: str = ""):
        event = AgentEvent(run_id=run_id, agent_name=agent_name, event_type=event_type, message=message)
        self.events.setdefault(run_id, []).append(event)


# Singleton instance
collector = MetricsCollector()
