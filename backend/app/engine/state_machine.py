"""Workflow state machine with valid transitions."""

from enum import Enum

class WorkflowState(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"

VALID_WORKFLOW_TRANSITIONS = {
    WorkflowState.PENDING: [WorkflowState.QUEUED, WorkflowState.CANCELLED],
    # QUEUED → FAILED covers pre-run errors like DAG validation
    # failures that abort the run before it ever reaches RUNNING.
    WorkflowState.QUEUED: [WorkflowState.RUNNING, WorkflowState.CANCELLED, WorkflowState.FAILED],
    WorkflowState.RUNNING: [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED],
    WorkflowState.COMPLETED: [],
    WorkflowState.FAILED: [WorkflowState.QUEUED],  # allow retry
    WorkflowState.CANCELLED: [],
}

VALID_STEP_TRANSITIONS = {
    StepState.PENDING: [StepState.RUNNING, StepState.SKIPPED],
    StepState.RUNNING: [StepState.COMPLETED, StepState.FAILED, StepState.RETRYING],
    StepState.COMPLETED: [],
    StepState.FAILED: [StepState.RETRYING, StepState.PENDING],
    StepState.SKIPPED: [],
    StepState.RETRYING: [StepState.RUNNING],
}

class InvalidTransitionError(Exception):
    pass

def transition_workflow(current: str, target: str) -> str:
    current_state = WorkflowState(current)
    target_state = WorkflowState(target)
    if target_state not in VALID_WORKFLOW_TRANSITIONS[current_state]:
        raise InvalidTransitionError(
            f"Cannot transition workflow from '{current}' to '{target}'. "
            f"Valid targets: {[s.value for s in VALID_WORKFLOW_TRANSITIONS[current_state]]}"
        )
    return target_state.value

def transition_step(current: str, target: str) -> str:
    current_state = StepState(current)
    target_state = StepState(target)
    if target_state not in VALID_STEP_TRANSITIONS[current_state]:
        raise InvalidTransitionError(
            f"Cannot transition step from '{current}' to '{target}'. "
            f"Valid targets: {[s.value for s in VALID_STEP_TRANSITIONS[current_state]]}"
        )
    return target_state.value
