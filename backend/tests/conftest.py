"""Shared fixtures for NexusForge tests.

Also sets fake environment variables for required settings BEFORE any
app module is imported, so importing `app.config` (which validates
DATABASE_URL and JWT_SECRET at module load time) does not crash when
tests run in CI or locally without a .env file.
"""

import os

# Must run BEFORE any `from app.*` import below, otherwise app.config
# raises RuntimeError on module load. CI and bare-repo test runs rely
# on this.
os.environ.setdefault(
    "DATABASE_URL", "postgresql://test_user:test_pass@localhost:5432/nexusforge_test"
)
os.environ.setdefault(
    "JWT_SECRET",
    "test-jwt-secret-for-pytest-only-do-not-use-in-production-32bytes",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("DEBUG", "false")

import pytest  # noqa: E402
from app.models.workflow import DAGDefinition, StepDefinition  # noqa: E402


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
