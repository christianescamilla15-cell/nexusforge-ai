"""Tests for DAG validation and parallel group computation."""

import pytest
from app.engine.dag import validate_dag, get_parallel_groups, DAGValidationError
from app.models.workflow import DAGDefinition, StepDefinition


# ---------- validate_dag ----------

def test_validate_linear_dag(linear_dag):
    order = validate_dag(linear_dag)
    assert order == ["A", "B", "C"]


def test_validate_diamond_dag(diamond_dag):
    order = validate_dag(diamond_dag)
    assert order.index("A") < order.index("B")
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("D")
    assert order.index("C") < order.index("D")


def test_validate_single_step(single_step_dag):
    order = validate_dag(single_step_dag)
    assert order == ["solo"]


def test_validate_cycle_detection():
    dag = DAGDefinition(steps=[
        StepDefinition(name="A", type="t", depends_on=["B"]),
        StepDefinition(name="B", type="t", depends_on=["A"]),
    ])
    with pytest.raises(DAGValidationError, match="cycle"):
        validate_dag(dag)


def test_validate_missing_dependency():
    dag = DAGDefinition(steps=[
        StepDefinition(name="A", type="t", depends_on=["nonexistent"]),
    ])
    with pytest.raises(DAGValidationError, match="unknown step"):
        validate_dag(dag)


def test_validate_duplicate_step_names():
    dag = DAGDefinition(steps=[
        StepDefinition(name="A", type="t"),
        StepDefinition(name="A", type="t"),
    ])
    with pytest.raises(DAGValidationError, match="Duplicate"):
        validate_dag(dag)


def test_validate_empty_steps():
    dag = DAGDefinition(steps=[])
    with pytest.raises(DAGValidationError, match="at least one step"):
        validate_dag(dag)


def test_validate_all_parallel(all_parallel_dag):
    order = validate_dag(all_parallel_dag)
    assert set(order) == {"X", "Y", "Z"}


# ---------- get_parallel_groups ----------

def test_parallel_groups_linear(linear_dag):
    order = validate_dag(linear_dag)
    groups = get_parallel_groups(linear_dag, order)
    assert groups == [["A"], ["B"], ["C"]]


def test_parallel_groups_diamond(diamond_dag):
    order = validate_dag(diamond_dag)
    groups = get_parallel_groups(diamond_dag, order)
    assert len(groups) == 3
    assert groups[0] == ["A"]
    assert set(groups[1]) == {"B", "C"}
    assert groups[2] == ["D"]


def test_parallel_groups_single_step(single_step_dag):
    order = validate_dag(single_step_dag)
    groups = get_parallel_groups(single_step_dag, order)
    assert groups == [["solo"]]


def test_parallel_groups_all_parallel(all_parallel_dag):
    order = validate_dag(all_parallel_dag)
    groups = get_parallel_groups(all_parallel_dag, order)
    assert len(groups) == 1
    assert set(groups[0]) == {"X", "Y", "Z"}


def test_parallel_groups_all_sequential(all_sequential_dag):
    order = validate_dag(all_sequential_dag)
    groups = get_parallel_groups(all_sequential_dag, order)
    assert len(groups) == 4
    assert groups == [["A"], ["B"], ["C"], ["D"]]


def test_complex_mixed_dag():
    """
    A ─→ B ─→ D
    A ─→ C ─→ E
              E ─→ F
    B + E → F
    """
    dag = DAGDefinition(steps=[
        StepDefinition(name="A", type="t"),
        StepDefinition(name="B", type="t", depends_on=["A"]),
        StepDefinition(name="C", type="t", depends_on=["A"]),
        StepDefinition(name="D", type="t", depends_on=["B"]),
        StepDefinition(name="E", type="t", depends_on=["C"]),
        StepDefinition(name="F", type="t", depends_on=["B", "E"]),
    ])
    order = validate_dag(dag)
    groups = get_parallel_groups(dag, order)
    # Depth: A=0, B=1, C=1, D=2, E=2, F=3
    assert groups[0] == ["A"]
    assert set(groups[1]) == {"B", "C"}
    assert set(groups[2]) == {"D", "E"}
    assert groups[3] == ["F"]


def test_validate_three_node_cycle():
    dag = DAGDefinition(steps=[
        StepDefinition(name="A", type="t", depends_on=["C"]),
        StepDefinition(name="B", type="t", depends_on=["A"]),
        StepDefinition(name="C", type="t", depends_on=["B"]),
    ])
    with pytest.raises(DAGValidationError, match="cycle"):
        validate_dag(dag)
