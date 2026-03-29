"""
Execution tracking data structures.

ExecutionContext carries per-run state through the engine pipeline.
ExecutionMetrics accumulates step-level aggregates for a single run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .interfaces import ExecutionTracker


@dataclass
class ExecutionMetrics:
    """Accumulated metrics for a single workflow execution."""

    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    retry_count: int = 0
    fallback_count: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0


@dataclass
class ExecutionContext:
    """Per-run context passed through the engine pipeline.

    Carries the tracker, correlation metadata, and running metrics
    so every component can emit events without coupling to infrastructure.
    """

    run_id: str
    workflow_name: str
    correlation_id: str | None = None
    tracker: ExecutionTracker | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
