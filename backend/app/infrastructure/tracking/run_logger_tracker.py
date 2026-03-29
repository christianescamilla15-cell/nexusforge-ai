"""
RunLoggerExecutionTracker — Adapter that bridges the ExecutionTracker
interface to the existing RunLogger persistence service.

Uses the Adapter pattern: the engine programs against ExecutionTracker,
while this class delegates every call to the synchronous RunLogger,
running blocking DB operations in a thread pool to stay async-safe.
"""
import asyncio
from functools import partial
from typing import Any

from app.domain.tracking.interfaces import ExecutionTracker
from app.services.run_logger import RunLogger


class RunLoggerExecutionTracker(ExecutionTracker):
    """Concrete tracker backed by RunLogger + SQLAlchemy."""

    def __init__(self, run_logger: RunLogger) -> None:
        self._rl = run_logger

    # ── helpers ──────────────────────────────

    async def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous RunLogger method in the default executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    # ── workflow level ───────────────────────

    async def workflow_started(
        self,
        run_id: str,
        workflow_name: str,
        topology: str,
        input_payload: dict[str, Any] | None = None,
    ) -> None:
        await self._run_sync(
            self._rl.start_workflow,
            workflow_name,
            topology,
            input_payload,
        )

    async def workflow_completed(
        self,
        run_id: str,
        output_payload: dict[str, Any] | None = None,
    ) -> None:
        await self._run_sync(
            self._rl.finish_workflow,
            run_id,
            output_payload,
        )

    async def workflow_failed(
        self,
        run_id: str,
        error_message: str,
    ) -> None:
        await self._run_sync(
            self._rl.fail_workflow,
            run_id,
            error_message,
        )

    # ── step level ───────────────────────────

    async def step_started(
        self,
        run_id: str,
        step_id: str,
        step_order: int,
        agent_name: str,
        input_payload: dict[str, Any] | None = None,
    ) -> None:
        await self._run_sync(
            self._rl.start_step,
            run_id,
            step_order,
            agent_name,
            input_payload,
        )

    async def step_completed(
        self,
        step_id: str,
        output_payload: dict[str, Any] | None = None,
        provider_name: str | None = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        await self._run_sync(
            self._rl.finish_step,
            step_id,
            output_payload,
            provider_name,
            tokens_used,
            cost_usd,
        )

    async def step_failed(
        self,
        step_id: str,
        error_message: str,
    ) -> None:
        await self._run_sync(
            self._rl.fail_step,
            step_id,
            error_message,
        )

    # ── retry & fallback ─────────────────────

    async def retry_recorded(
        self,
        step_id: str,
        attempt: int,
    ) -> None:
        await self._run_sync(
            self._rl.log_retry,
            step_id,
            attempt,
        )

    async def fallback_recorded(
        self,
        step_id: str,
        from_provider: str,
        to_provider: str,
    ) -> None:
        await self._run_sync(
            self._rl.log_fallback,
            step_id,
            from_provider,
            to_provider,
        )

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
        await self._run_sync(
            self._rl.log_event,
            run_id,
            agent_name,
            event_type,
            step_id,
            message,
            metadata,
        )

    async def checkpoint_created(
        self,
        run_id: str,
        step_id: str,
        checkpoint_data: dict[str, Any],
    ) -> None:
        # RunLogger has no dedicated checkpoint method; store as an event.
        await self._run_sync(
            self._rl.log_event,
            run_id,
            "system",
            "checkpoint_created",
            step_id,
            f"Checkpoint created for step {step_id}",
            checkpoint_data,
        )
