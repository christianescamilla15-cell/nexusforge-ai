"""Workflow CRUD routes."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from app.auth.jwt_handler import verify_token
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


def _get_user_id(request: Request) -> str:
    """Extract and verify user from JWT. Raises 401 if missing/invalid."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login required")
    token_data = verify_token(auth[7:])
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return token_data["sub"]


@router.post("/", status_code=201, response_model=WorkflowResponse)
async def create_workflow(body: WorkflowCreate, request: Request):
    """Create a new workflow after validating its DAG definition."""
    user_id = _get_user_id(request)  # require auth
    try:
        validate_dag(body.dag_definition)
    except DAGValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid workflow DAG")

    try:
        pool = await get_db_pool()
        dag_json = json.dumps(body.dag_definition.model_dump())
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO workflows (name, description, dag_definition, version, status, user_id)
                   VALUES ($1, $2, $3::jsonb, 1, 'active', $4::uuid)
                   RETURNING id, name, description, dag_definition, version, status, created_at, updated_at""",
                body.name,
                body.description,
                dag_json,
                user_id,
            )
        return _row_to_response(row)
    except Exception as exc:
        logger.exception("Failed to create workflow")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(request: Request, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    """List workflows with pagination."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, name, description, dag_definition, version, status, created_at, updated_at
                   FROM workflows
                   WHERE status != 'archived'
                     AND user_id = $1::uuid
                   ORDER BY created_at DESC
                   OFFSET $2 LIMIT $3""",
                user_id,
                skip,
                limit,
            )
        return [_row_to_response(r) for r in rows]
    except Exception as exc:
        logger.exception("Failed to list workflows")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID, request: Request):
    """Get a single workflow by ID."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT id, name, description, dag_definition, version, status, created_at, updated_at, user_id
                   FROM workflows WHERE id = $1""",
                workflow_id,
            )
        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")
        # Allow access if workflow has no owner (shared/legacy) or user owns it
        if row["user_id"] and str(row["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="You don't own this workflow")
        return _row_to_response(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get workflow")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: UUID, body: WorkflowUpdate, request: Request):
    """Update an existing workflow. If dag_definition is provided, validate it first."""
    user_id = _get_user_id(request)
    if body.dag_definition is not None:
        try:
            validate_dag(body.dag_definition)
        except DAGValidationError as exc:
            raise HTTPException(status_code=422, detail="Invalid workflow DAG")

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT id, user_id FROM workflows WHERE id = $1", workflow_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Workflow not found")
            if existing["user_id"] and str(existing["user_id"]) != user_id:
                raise HTTPException(status_code=403, detail="You don't own this workflow")

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

            # mythos: sqli-safe — `sets` is built from hardcoded checks
            # on body.name / body.description / body.dag_definition /
            # body.status above. Each entry is a constant `name = $N`
            # fragment with parameterized values.
            query = f"""UPDATE workflows SET {', '.join(sets)}
                        WHERE id = ${idx}
                        RETURNING id, name, description, dag_definition, version, status, created_at, updated_at"""

            row = await conn.fetchrow(query, *params)
        return _row_to_response(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update workflow")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{workflow_id}", status_code=200)
async def delete_workflow(workflow_id: UUID, request: Request):
    """Soft-delete a workflow by setting status to 'archived'. Checks ownership."""
    user_id = _get_user_id(request)
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Ownership check
            owner = await conn.fetchval("SELECT user_id FROM workflows WHERE id = $1", workflow_id)
            if owner and user_id and str(owner) != user_id:
                raise HTTPException(status_code=403, detail="You don't own this workflow")
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
        raise HTTPException(status_code=500, detail="Internal server error")


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
