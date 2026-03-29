"""
Factory for assembling the ExecutionTracker chain.

Builds: RunLogger -> RunLoggerExecutionTracker -> SafeExecutionTracker

Usage:
    from app.services.execution_tracker_factory import create_execution_tracker
    tracker = create_execution_tracker(db_session)
"""
from sqlalchemy.orm import Session

from app.domain.tracking.interfaces import ExecutionTracker


def create_execution_tracker(db_session: Session) -> ExecutionTracker:
    """Create a production-ready ExecutionTracker backed by RunLogger.

    The returned tracker is wrapped in SafeExecutionTracker so that
    any persistence error is logged but never propagates to the engine.
    """
    from app.services.run_logger import RunLogger
    from app.infrastructure.tracking.run_logger_tracker import RunLoggerExecutionTracker
    from app.infrastructure.tracking.safe_tracker import SafeExecutionTracker

    run_logger = RunLogger(db_session)
    tracker = RunLoggerExecutionTracker(run_logger)
    return SafeExecutionTracker(tracker)
