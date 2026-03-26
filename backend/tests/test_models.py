"""Tests for Pydantic model validation."""

import pytest
from pydantic import ValidationError
from app.models.workflow import WorkflowCreate, DAGDefinition, StepDefinition
from app.models.execution import ExecutionTrigger
from app.models.document import DocumentUpload, DocumentSearch


def test_workflow_create_valid(sample_workflow_data):
    wf = WorkflowCreate(**sample_workflow_data)
    assert wf.name == "Test Workflow"
    assert len(wf.dag_definition.steps) == 2


def test_workflow_create_empty_name_fails():
    with pytest.raises(ValidationError):
        WorkflowCreate(name="", dag_definition=DAGDefinition(steps=[
            StepDefinition(name="s", type="t"),
        ]))


def test_dag_definition_with_steps():
    dag = DAGDefinition(steps=[
        StepDefinition(name="A", type="classifier"),
        StepDefinition(name="B", type="extractor", depends_on=["A"]),
    ])
    assert len(dag.steps) == 2
    assert dag.steps[1].depends_on == ["A"]


def test_execution_trigger_validation():
    trigger = ExecutionTrigger(workflow_id="550e8400-e29b-41d4-a716-446655440000")
    assert trigger.trigger_type == "manual"
    assert trigger.input_data == {}


def test_execution_trigger_invalid_uuid():
    with pytest.raises(ValidationError):
        ExecutionTrigger(workflow_id="not-a-uuid")


def test_document_upload_min_content_length():
    with pytest.raises(ValidationError):
        DocumentUpload(title="Test", content="short")


def test_document_upload_valid(sample_document_data):
    doc = DocumentUpload(**sample_document_data)
    assert doc.title == "Test Document"
    assert doc.language == "en"


def test_document_search_min_query_length():
    with pytest.raises(ValidationError):
        DocumentSearch(query="")


def test_document_search_valid():
    s = DocumentSearch(query="machine learning")
    assert s.top_k == 5


def test_step_definition_defaults():
    step = StepDefinition(name="s1", type="classifier")
    assert step.config == {}
    assert step.depends_on == []
    assert step.retry_max == 3
    assert step.timeout_seconds == 300
