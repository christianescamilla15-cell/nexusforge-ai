"""
CompositeExecutionTracker — Fans out every tracking call to multiple
ExecutionTracker implementations so the engine can feed several
observability backends (e.g., RunLogger + MetricsCollector) from a
single tracker reference.
"""
import asyncio
import logging
from typing import Any

from app.domain.tracking.interfaces import ExecutionTracker

logger = logging.getLogger(__name__)


class CompositeExecutionTracker(ExecutionTracker):
    """Delegates every call to all wrapped trackers, best-effort."""

    def __init__(self, *trackers: ExecutionTracker) -> None:
        self._trackers = trackers

    async def _fan_out(self, method_name: str, *args, **kwargs):
        for tracker in self._trackers:
            try:
                await getattr(tracker, method_name)(*args, **kwargs)
            except Exception:
                logger.warning(
                    "CompositeTracker: %s failed on %s",
                    method_name,
                    type(tracker).__name__,
                    exc_info=True,
                )

    # ── workflow level ───────────────────────

    async def workflow_started(
        self, run_id: str, workflow_name: str, topology: str,
        input_payload: dict[str, Any] | None = None,
    ) -> None:
        await self._fan_out("workflow_started", run_id, workflow_name, topology, input_payload)

    async def workflow_completed(
        self, run_id: str, output_payload: dict[str, Any] | None = None,
    ) -> None:
        await self._fan_out("workflow_completed", run_id, output_payload)

    async def workflow_failed(self, run_id: str, error_message: str) -> None:
        await self._fan_out("workflow_failed", run_id, error_message)

    # ── step level ───────────────────────────

    async def step_started(
        self, run_id: str, step_id: str, step_order: int,
        agent_name: str, input_payload: dict[str, Any] | None = None,
    ) -> None:
        await self._fan_out("step_started", run_id, step_id, step_order, agent_name, input_payload)

    async def step_completed(
        self, step_id: str, output_payload: dict[str, Any] | None = None,
        provider_name: str | None = None, tokens_used: int = 0, cost_usd: float = 0.0,
    ) -> None:
        await self._fan_out("step_completed", step_id, output_payload, provider_name, tokens_used, cost_usd)

    async def step_failed(self, step_id: str, error_message: str) -> None:
        await self._fan_out("step_failed", step_id, error_message)

    # ── retry & fallback ─────────────────────

    async def retry_recorded(self, step_id: str, attempt: int) -> None:
        await self._fan_out("retry_recorded", step_id, attempt)

    async def fallback_recorded(self, step_id: str, from_provider: str, to_provider: str) -> None:
        await self._fan_out("fallback_recorded", step_id, from_provider, to_provider)

    # ── events & checkpoints ─────────────────

    async def agent_event(
        self, run_id: str, agent_name: str, event_type: str,
        step_id: str | None = None, message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._fan_out("agent_event", run_id, agent_name, event_type, step_id, message, metadata)

    async def checkpoint_created(
        self, run_id: str, step_id: str, checkpoint_data: dict[str, Any],
    ) -> None:
        await self._fan_out("checkpoint_created", run_id, step_id, checkpoint_data)
