"""
Tracking package — cross-cutting observability for the orchestration engine.

Integration points:
- engine/executor.py → workflow lifecycle
- engine/step_runner.py → step lifecycle
- engine/checkpoint.py → checkpoint events
- llm/router.py → provider fallback/circuit breaker events
"""
from app.domain.tracking.interfaces import ExecutionTracker
from app.domain.tracking.events import ExecutionContext, ExecutionMetrics
from app.infrastructure.tracking.safe_tracker import SafeExecutionTracker
from app.infrastructure.tracking.step_wrapper import StepExecutionWrapper
from app.services.execution_tracker_factory import create_execution_tracker

__all__ = [
    "ExecutionTracker",
    "ExecutionContext",
    "ExecutionMetrics",
    "SafeExecutionTracker",
    "StepExecutionWrapper",
    "create_execution_tracker",
]
