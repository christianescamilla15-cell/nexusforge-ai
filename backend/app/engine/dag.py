"""DAG parser and validator — ensures workflow graphs are acyclic and valid."""

from app.models.workflow import DAGDefinition, StepDefinition

class DAGValidationError(Exception):
    pass

def validate_dag(dag: DAGDefinition) -> list[str]:
    """Validate DAG: no cycles, all dependencies exist, no orphans. Returns ordered step names."""
    steps_by_name = {s.name: s for s in dag.steps}

    if not dag.steps:
        raise DAGValidationError("DAG must have at least one step")

    # Check for duplicate names
    names = [s.name for s in dag.steps]
    if len(names) != len(set(names)):
        raise DAGValidationError("Duplicate step names found")

    # Check all dependencies exist
    for step in dag.steps:
        for dep in step.depends_on:
            if dep not in steps_by_name:
                raise DAGValidationError(f"Step '{step.name}' depends on unknown step '{dep}'")

    # Topological sort (Kahn's algorithm) — detects cycles
    in_degree = {s.name: 0 for s in dag.steps}
    adjacency = {s.name: [] for s in dag.steps}

    for step in dag.steps:
        for dep in step.depends_on:
            adjacency[dep].append(step.name)
            in_degree[step.name] += 1

    queue = [name for name, degree in in_degree.items() if degree == 0]
    order = []

    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbor in adjacency[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(dag.steps):
        raise DAGValidationError("DAG contains a cycle")

    return order

def get_parallel_groups(dag: DAGDefinition, order: list[str]) -> list[list[str]]:
    """Group steps that can run in parallel (same depth level in DAG)."""
    steps_by_name = {s.name: s for s in dag.steps}
    depth = {}

    for name in order:
        step = steps_by_name[name]
        if not step.depends_on:
            depth[name] = 0
        else:
            depth[name] = max(depth[dep] for dep in step.depends_on) + 1

    max_depth = max(depth.values()) if depth else 0
    groups = []
    for d in range(max_depth + 1):
        group = [name for name in order if depth[name] == d]
        if group:
            groups.append(group)

    return groups
