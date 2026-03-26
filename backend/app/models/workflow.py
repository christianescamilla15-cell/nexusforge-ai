from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

class StepDefinition(BaseModel):
    name: str
    type: str  # agent_type or built-in step type
    config: dict = {}
    depends_on: list[str] = []  # names of steps this depends on
    retry_max: int = 3
    timeout_seconds: int = 300

class DAGDefinition(BaseModel):
    steps: list[StepDefinition]

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    dag_definition: DAGDefinition

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dag_definition: Optional[DAGDefinition] = None
    status: Optional[str] = None

class WorkflowResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    dag_definition: dict
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
