"""
MetricsCollectorTracker — ExecutionTracker implementation that populates
the in-memory MetricsCollector singleton so that dashboard API routes
(/api/runs/*) serve live execution data.

This bridges the gap between the engine (which calls ctx.tracker.*)
and the dashboard routes (which read from collector.*).
"""
import logging
from typing import Any

from app.domain.tracking.interfaces import ExecutionTracker
from app.metrics.collector import collector
from app.models.workflow_run import RunStatus

logger = logging.getLogger(__name__)


class MetricsCollectorTracker(ExecutionTracker):
    """Feeds the in-memory MetricsCollector from ExecutionTracker calls."""

    def __init__(self) -> None:
        # Maps step_id -> WorkflowStep object for later updates
        self._step_map: dict[str, Any] = {}

    # ── workflow level ───────────────────────

    async def workflow_started(
        self, run_id: str, workflow_name: str, topology: str,
        input_payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            run = collector.start_run(workflow_name, topology)
            # The collector generates its own id; remap to the real run_id
            # so dashboard lookups by run_id work correctly.
            if run.id != run_id:
                collector.runs.pop(run.id, None)
                steps = collector.steps.pop(run.id, [])
                events = collector.events.pop(run.id, [])
                run.id = run_id
                collector.runs[run_id] = run
                collector.steps[run_id] = steps
                collector.events[run_id] = events
        except Exception:
            logger.warning("MetricsCollectorTracker.workflow_started failed", exc_info=True)

    async def workflow_completed(
        self, run_id: str, output_payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            collector.end_run(run_id, RunStatus.COMPLETED)
        except Exception:
            logger.warning("MetricsCollectorTracker.workflow_completed failed", exc_info=True)

    async def workflow_failed(self, run_id: str, error_message: str) -> None:
        try:
            collector.end_run(run_id, RunStatus.FAILED)
        except Exception:
            logger.warning("MetricsCollectorTracker.workflow_failed failed", exc_info=True)

    # ── step level ───────────────────────────

    async def step_started(
        self, run_id: str, step_id: str, step_order: int,
        agent_name: str, input_payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            step = collector.start_step(run_id, agent_name, step_order)
            # Remap to the real step_id
            step.id = step_id
            self._step_map[step_id] = step
        except Exception:
            logger.warning("MetricsCollectorTracker.step_started failed", exc_info=True)

    async def step_completed(
        self, step_id: str, output_payload: dict[str, Any] | None = None,
        provider_name: str | None = None, tokens_used: int = 0, cost_usd: float = 0.0,
    ) -> None:
        try:
            step = self._step_map.get(step_id)
            if step:
                collector.end_step(step, provider=provider_name or "", output_summary=str(output_payload)[:200] if output_payload else "")
        except Exception:
            logger.warning("MetricsCollectorTracker.step_completed failed", exc_info=True)

    async def step_failed(self, step_id: str, error_message: str) -> None:
        try:
            step = self._step_map.get(step_id)
            if step:
                collector.fail_step(step, error_message)
        except Exception:
            logger.warning("MetricsCollectorTracker.step_failed failed", exc_info=True)

    # ── retry & fallback ─────────────────────

    async def retry_recorded(self, step_id: str, attempt: int) -> None:
        try:
            step = self._step_map.get(step_id)
            if step:
                step.retry_count = attempt
                collector.log_retry(step.run_id, step.agent_name, attempt)
        except Exception:
            logger.warning("MetricsCollectorTracker.retry_recorded failed", exc_info=True)

    async def fallback_recorded(self, step_id: str, from_provider: str, to_provider: str) -> None:
        try:
            step = self._step_map.get(step_id)
            if step:
                collector.log_fallback(step.run_id, step.agent_name, from_provider, to_provider)
        except Exception:
            logger.warning("MetricsCollectorTracker.fallback_recorded failed", exc_info=True)

    # ── events & checkpoints ─────────────────

    async def agent_event(
        self, run_id: str, agent_name: str, event_type: str,
        step_id: str | None = None, message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # Generic events are already captured by the specific methods above;
        # no additional action needed for the collector.
        pass

    async def checkpoint_created(
        self, run_id: str, step_id: str, checkpoint_data: dict[str, Any],
    ) -> None:
        # Checkpoints are not tracked by MetricsCollector.
        pass
