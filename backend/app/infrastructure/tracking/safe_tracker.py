"""
SafeExecutionTracker — Decorator that wraps any ExecutionTracker
and swallows exceptions so tracking failures never break a workflow.

Every method delegates to the inner tracker inside a try/except;
errors are logged at WARNING level but never re-raised.
"""
import logging
from typing import Any

from app.domain.tracking.interfaces import ExecutionTracker

logger = logging.getLogger(__name__)


class SafeExecutionTracker(ExecutionTracker):
    """Exception-safe wrapper around any ExecutionTracker implementation."""

    def __init__(self, inner: ExecutionTracker) -> None:
        self.inner = inner

    # ── workflow level ───────────────────────

    async def workflow_started(
        self,
        run_id: str,
        workflow_name: str,
        topology: str,
        input_payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            await self.inner.workflow_started(run_id, workflow_name, topology, input_payload)
        except Exception:
            logger.warning("Tracker error in workflow_started (run=%s)", run_id, exc_info=True)

    async def workflow_completed(
        self,
        run_id: str,
        output_payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            await self.inner.workflow_completed(run_id, output_payload)
        except Exception:
            logger.warning("Tracker error in workflow_completed (run=%s)", run_id, exc_info=True)

    async def workflow_failed(
        self,
        run_id: str,
        error_message: str,
    ) -> None:
        try:
            await self.inner.workflow_failed(run_id, error_message)
        except Exception:
            logger.warning("Tracker error in workflow_failed (run=%s)", run_id, exc_info=True)

    # ── step level ───────────────────────────

    async def step_started(
        self,
        run_id: str,
        step_id: str,
        step_order: int,
        agent_name: str,
        input_payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            await self.inner.step_started(run_id, step_id, step_order, agent_name, input_payload)
        except Exception:
            logger.warning("Tracker error in step_started (step=%s)", step_id, exc_info=True)

    async def step_completed(
        self,
        step_id: str,
        output_payload: dict[str, Any] | None = None,
        provider_name: str | None = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        try:
            await self.inner.step_completed(step_id, output_payload, provider_name, tokens_used, cost_usd)
        except Exception:
            logger.warning("Tracker error in step_completed (step=%s)", step_id, exc_info=True)

    async def step_failed(
        self,
        step_id: str,
        error_message: str,
    ) -> None:
        try:
            await self.inner.step_failed(step_id, error_message)
        except Exception:
            logger.warning("Tracker error in step_failed (step=%s)", step_id, exc_info=True)

    # ── retry & fallback ─────────────────────

    async def retry_recorded(
        self,
        step_id: str,
        attempt: int,
    ) -> None:
        try:
            await self.inner.retry_recorded(step_id, attempt)
        except Exception:
            logger.warning("Tracker error in retry_recorded (step=%s)", step_id, exc_info=True)

    async def fallback_recorded(
        self,
        step_id: str,
        from_provider: str,
        to_provider: str,
    ) -> None:
        try:
            await self.inner.fallback_recorded(step_id, from_provider, to_provider)
        except Exception:
            logger.warning("Tracker error in fallback_recorded (step=%s)", step_id, exc_info=True)

    # ── events & checkpoints ─────────────────

    async def agent_event(
        self,
        run_id: str,
        agent_name: str,
        event_type: str,
        step_id: str | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            await self.inner.agent_event(run_id, agent_name, event_type, step_id, message, metadata)
        except Exception:
            logger.warning("Tracker error in agent_event (run=%s)", run_id, exc_info=True)

    async def checkpoint_created(
        self,
        run_id: str,
        step_id: str,
        checkpoint_data: dict[str, Any],
    ) -> None:
        try:
            await self.inner.checkpoint_created(run_id, step_id, checkpoint_data)
        except Exception:
            logger.warning("Tracker error in checkpoint_created (step=%s)", step_id, exc_info=True)
