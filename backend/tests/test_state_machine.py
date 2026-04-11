"""Tests for workflow and step state machine transitions."""

import pytest
from app.engine.state_machine import (
    transition_workflow,
    transition_step,
    InvalidTransitionError,
)


# ---------- Workflow transitions ----------

def test_workflow_pending_to_queued():
    assert transition_workflow("pending", "queued") == "queued"


def test_workflow_queued_to_running():
    assert transition_workflow("queued", "running") == "running"


def test_workflow_running_to_completed():
    assert transition_workflow("running", "completed") == "completed"


def test_workflow_running_to_failed():
    assert transition_workflow("running", "failed") == "failed"


def test_workflow_running_to_cancelled():
    assert transition_workflow("running", "cancelled") == "cancelled"


def test_workflow_completed_to_running_invalid():
    with pytest.raises(InvalidTransitionError):
        transition_workflow("completed", "running")


def test_workflow_cancelled_to_running_invalid():
    with pytest.raises(InvalidTransitionError):
        transition_workflow("cancelled", "running")


def test_workflow_failed_to_queued():
    """Failed workflows can be re-queued for retry."""
    assert transition_workflow("failed", "queued") == "queued"


def test_workflow_pending_to_cancelled():
    assert transition_workflow("pending", "cancelled") == "cancelled"


# ---------- Step transitions ----------

def test_step_pending_to_running():
    assert transition_step("pending", "running") == "running"


def test_step_running_to_completed():
    assert transition_step("running", "completed") == "completed"


def test_step_running_to_retrying():
    assert transition_step("running", "retrying") == "retrying"


def test_step_running_to_failed():
    assert transition_step("running", "failed") == "failed"


def test_step_completed_to_running_invalid():
    with pytest.raises(InvalidTransitionError):
        transition_step("completed", "running")


def test_step_pending_to_skipped():
    assert transition_step("pending", "skipped") == "skipped"


def test_step_retrying_to_running():
    assert transition_step("retrying", "running") == "running"


def test_step_failed_to_retrying():
    assert transition_step("failed", "retrying") == "retrying"


# ---------- Enforcement: new QUEUED → FAILED transition ----------
#
# Pre-run errors (DAG validation, config resolution) need to move a
# queued run directly to failed without ever reaching RUNNING. This
# transition was added in the state machine enforcement pass so that
# backend/app/engine/executor.py can record DAG validation failures
# without a spurious state-machine violation.


def test_workflow_queued_to_failed_pre_run_error():
    """DAG validation error path: queued → failed without entering running."""
    assert transition_workflow("queued", "failed") == "failed"


def test_workflow_queued_to_completed_invalid():
    """A queued run cannot skip straight to completed — it must run first."""
    with pytest.raises(InvalidTransitionError):
        transition_workflow("queued", "completed")


def test_workflow_completed_to_failed_invalid():
    """Completed is terminal — any transition out of it should raise."""
    with pytest.raises(InvalidTransitionError):
        transition_workflow("completed", "failed")


def test_step_retrying_to_failed_invalid_without_normalization():
    """In-code pattern: step_runner normalizes retrying→running before
    the failure path. A direct retrying→failed (skipping that
    normalization) is NOT allowed and must raise, catching the bug
    where a developer forgets the normalization step."""
    with pytest.raises(InvalidTransitionError):
        transition_step("retrying", "failed")
