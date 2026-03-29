"""
ExecutionTracker — Abstract interface for workflow execution observability.

Defines the contract that all tracker implementations must follow,
enabling the engine to remain decoupled from any specific persistence
or observability backend.
"""
from abc import ABC, abstractmethod
from typing import Any


class ExecutionTracker(ABC):
    """Abstract base class for tracking workflow execution lifecycle."""

    # ─────────────────────────────────────────
    # WORKFLOW LEVEL
    # ─────────────────────────────────────────

    @abstractmethod
    async def workflow_started(
        self,
        run_id: str,
        workflow_name: str,
        topology: str,
        input_payload: dict[str, Any] | None = None,
    ) -> None:
        """Record the start of a workflow run."""

    @abstractmethod
    async def workflow_completed(
        self,
        run_id: str,
        output_payload: dict[str, Any] | None = None,
    ) -> None:
        """Record successful completion of a workflow run."""

    @abstractmethod
    async def workflow_failed(
        self,
        run_id: str,
        error_message: str,
    ) -> None:
        """Record failure of a workflow run."""

    # ─────────────────────────────────────────
    # STEP LEVEL
    # ─────────────────────────────────────────

    @abstractmethod
    async def step_started(
        self,
        run_id: str,
        step_id: str,
        step_order: int,
        agent_name: str,
        input_payload: dict[str, Any] | None = None,
    ) -> None:
        """Record the start of a workflow step."""

    @abstractmethod
    async def step_completed(
        self,
        step_id: str,
        output_payload: dict[str, Any] | None = None,
        provider_name: str | None = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Record successful completion of a workflow step."""

    @abstractmethod
    async def step_failed(
        self,
        step_id: str,
        error_message: str,
    ) -> None:
        """Record failure of a workflow step."""

    # ─────────────────────────────────────────
    # RETRY & FALLBACK
    # ─────────────────────────────────────────

    @abstractmethod
    async def retry_recorded(
        self,
        step_id: str,
        attempt: int,
    ) -> None:
        """Record a retry attempt for a step."""

    @abstractmethod
    async def fallback_recorded(
        self,
        step_id: str,
        from_provider: str,
        to_provider: str,
    ) -> None:
        """Record a provider fallback for a step."""

    # ─────────────────────────────────────────
    # EVENTS & CHECKPOINTS
    # ─────────────────────────────────────────

    @abstractmethod
    async def agent_event(
        self,
        run_id: str,
        agent_name: str,
        event_type: str,
        step_id: str | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a generic agent event for observability."""

    @abstractmethod
    async def checkpoint_created(
        self,
        run_id: str,
        step_id: str,
        checkpoint_data: dict[str, Any],
    ) -> None:
        """Record a checkpoint snapshot for recovery."""
