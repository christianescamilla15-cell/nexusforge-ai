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
