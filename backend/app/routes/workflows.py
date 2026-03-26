"""Workflow CRUD routes."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db.client import get_db_pool
from app.engine.dag import validate_dag, DAGValidationError
from app.models.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    DAGDefinition,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", status_code=201, response_model=WorkflowResponse)
async def create_workflow(body: WorkflowCreate):
    """Create a new workflow after validating its DAG definition."""
    # Validate the DAG before persisting
    try:
        validate_dag(body.dag_definition)
    except DAGValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid DAG: {exc}")

    try:
        pool = await get_db_pool()
        dag_json = json.dumps(body.dag_definition.model_dump())
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO workflows (name, description, dag_definition, version, status)
                   VALUES ($1, $2, $3::jsonb, 1, 'active')
                   RETURNING id, name, description, dag_definition, version, status, created_at, updated_at""",
                body.name,
                body.description,
                dag_json,
            )
        return _row_to_response(row)
    except Exception as exc:
        logger.exception("Failed to create workflow")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    """List workflows with pagination."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, name, description, dag_definition, version, status, created_at, updated_at
                   FROM workflows
                   WHERE status != 'archived'
                   ORDER BY created_at DESC
                   OFFSET $1 LIMIT $2""",
                skip,
                limit,
            )
        return [_row_to_response(r) for r in rows]
    except Exception as exc:
        logger.exception("Failed to list workflows")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID):
    """Get a single workflow by ID."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, name, description, dag_definition, version, status, created_at, updated_at
                   FROM workflows WHERE id = $1""",
                workflow_id,
            )
        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return _row_to_response(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get workflow")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: UUID, body: WorkflowUpdate):
    """Update an existing workflow. If dag_definition is provided, validate it first."""
    if body.dag_definition is not None:
        try:
            validate_dag(body.dag_definition)
        except DAGValidationError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid DAG: {exc}")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT id FROM workflows WHERE id = $1", workflow_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Workflow not found")

            sets = []
            params = []
            idx = 1

            if body.name is not None:
                sets.append(f"name = ${idx}")
                params.append(body.name)
                idx += 1
            if body.description is not None:
                sets.append(f"description = ${idx}")
                params.append(body.description)
                idx += 1
            if body.dag_definition is not None:
                sets.append(f"dag_definition = ${idx}::jsonb")
                params.append(json.dumps(body.dag_definition.model_dump()))
                idx += 1
                sets.append(f"version = version + 1")
            if body.status is not None:
                sets.append(f"status = ${idx}")
                params.append(body.status)
                idx += 1

            if not sets:
                raise HTTPException(status_code=422, detail="No fields to update")

            sets.append("updated_at = now()")
            params.append(workflow_id)

            query = f"""UPDATE workflows SET {', '.join(sets)}
                        WHERE id = ${idx}
                        RETURNING id, name, description, dag_definition, version, status, created_at, updated_at"""

            row = await conn.fetchrow(query, *params)
        return _row_to_response(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update workflow")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{workflow_id}", status_code=200)
async def delete_workflow(workflow_id: UUID):
    """Soft-delete a workflow by setting status to 'archived'."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE workflows SET status = 'archived', updated_at = now() WHERE id = $1 AND status != 'archived'",
                workflow_id,
            )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Workflow not found or already archived")
        return {"detail": "Workflow archived", "id": str(workflow_id)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete workflow")
        raise HTTPException(status_code=500, detail=str(exc))


def _row_to_response(row) -> WorkflowResponse:
    dag = row["dag_definition"]
    if isinstance(dag, str):
        dag = json.loads(dag)
    return WorkflowResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        dag_definition=dag,
        version=row["version"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
