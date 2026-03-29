"""
StepExecutionWrapper — Wraps individual step execution with automatic
tracking, timing, and metrics accumulation.

Usage:
    wrapper = StepExecutionWrapper()
    result = await wrapper.execute(ctx, step_id, step_order, agent_name, func, step_input)
"""
import time
from typing import Any, Callable, Awaitable

from app.domain.tracking.events import ExecutionContext


class StepExecutionWrapper:
    """Decorates step execution with lifecycle tracking and metrics."""

    async def execute(
        self,
        ctx: ExecutionContext,
        step_id: str,
        step_order: int,
        agent_name: str,
        func: Callable[..., Awaitable[Any]],
        step_input: dict[str, Any] | None = None,
    ) -> Any:
        """Execute *func* while tracking start/complete/fail and updating metrics.

        Args:
            ctx: The current execution context (carries tracker + metrics).
            step_id: Unique identifier for this step instance.
            step_order: Ordinal position of the step in the workflow.
            agent_name: Name of the agent responsible for the step.
            func: Async callable that performs the actual work.
            step_input: Optional input payload forwarded to the tracker.

        Returns:
            The value returned by *func*.

        Raises:
            Re-raises any exception from *func* after recording the failure.
        """
        ctx.metrics.total_steps += 1

        # ── notify step started ──────────────
        if ctx.tracker:
            await ctx.tracker.step_started(
                run_id=ctx.run_id,
                step_id=step_id,
                step_order=step_order,
                agent_name=agent_name,
                input_payload=step_input,
            )

        start_ns = time.perf_counter_ns()

        try:
            result = await func(step_input)
        except Exception as exc:
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
            ctx.metrics.failed_steps += 1
            ctx.metrics.total_latency_ms += elapsed_ms

            if ctx.tracker:
                await ctx.tracker.step_failed(step_id, str(exc))

            raise

        # ── success path ─────────────────────
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000
        ctx.metrics.completed_steps += 1
        ctx.metrics.total_latency_ms += elapsed_ms

        # Extract token/cost info from result if available
        tokens_used = 0
        cost_usd = 0.0
        provider_name: str | None = None
        output_payload: dict[str, Any] | None = None

        if isinstance(result, dict):
            tokens_used = result.get("tokens_used", 0)
            cost_usd = result.get("cost_usd", 0.0)
            provider_name = result.get("provider_name")
            output_payload = result

        ctx.metrics.total_tokens += tokens_used
        ctx.metrics.total_cost_usd += cost_usd

        if ctx.tracker:
            await ctx.tracker.step_completed(
                step_id=step_id,
                output_payload=output_payload,
                provider_name=provider_name,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
            )

        return result
