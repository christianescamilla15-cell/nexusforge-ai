"""Shared fixtures for NexusForge tests."""

import pytest
from app.models.workflow import DAGDefinition, StepDefinition


@pytest.fixture
def linear_dag():
    """A → B → C linear DAG."""
    return DAGDefinition(steps=[
        StepDefinition(name="A", type="classifier"),
        StepDefinition(name="B", type="extractor", depends_on=["A"]),
        StepDefinition(name="C", type="summarizer", depends_on=["B"]),
    ])


@pytest.fixture
def diamond_dag():
    """Diamond: A → B, A → C, B+C → D."""
    return DAGDefinition(steps=[
        StepDefinition(name="A", type="classifier"),
        StepDefinition(name="B", type="extractor", depends_on=["A"]),
        StepDefinition(name="C", type="analyzer", depends_on=["A"]),
        StepDefinition(name="D", type="reporter", depends_on=["B", "C"]),
    ])


@pytest.fixture
def single_step_dag():
    """Single step DAG."""
    return DAGDefinition(steps=[
        StepDefinition(name="solo", type="classifier"),
    ])


@pytest.fixture
def all_parallel_dag():
    """Three steps with no dependencies — all parallel."""
    return DAGDefinition(steps=[
        StepDefinition(name="X", type="classifier"),
        StepDefinition(name="Y", type="extractor"),
        StepDefinition(name="Z", type="analyzer"),
    ])


@pytest.fixture
def all_sequential_dag():
    """Fully sequential: A → B → C → D."""
    return DAGDefinition(steps=[
        StepDefinition(name="A", type="classifier"),
        StepDefinition(name="B", type="extractor", depends_on=["A"]),
        StepDefinition(name="C", type="analyzer", depends_on=["B"]),
        StepDefinition(name="D", type="reporter", depends_on=["C"]),
    ])


@pytest.fixture
def sample_workflow_data():
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "dag_definition": {
            "steps": [
                {"name": "step1", "type": "classifier", "depends_on": [], "config": {}, "retry_max": 3, "timeout_seconds": 300},
                {"name": "step2", "type": "summarizer", "depends_on": ["step1"], "config": {}, "retry_max": 3, "timeout_seconds": 300},
            ]
        },
    }


@pytest.fixture
def sample_document_data():
    return {
        "title": "Test Document",
        "content": "This is a test document with enough content to pass validation rules.",
        "file_type": "text",
        "language": "en",
        "metadata": {"source": "test"},
    }
