from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from uuid import UUID

class ExecutionTrigger(BaseModel):
    workflow_id: UUID
    trigger_type: str = "manual"
    input_data: dict = {}

class StepExecutionResponse(BaseModel):
    id: UUID
    step_name: str
    step_type: str
    agent_type: Optional[str]
    status: str
    input_data: Optional[dict]
    output_data: Optional[dict]
    error_message: Optional[str]
    retry_count: int
    tokens_used: int
    cost_usd: float
    duration_ms: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class ExecutionResponse(BaseModel):
    model_config = {"extra": "allow"}

    id: UUID
    workflow_id: UUID
    workflow_name: Optional[str] = "Workflow"
    status: str
    trigger_type: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    total_tokens: int
    total_cost_usd: float
    metadata: dict
    created_at: datetime
    steps: list[StepExecutionResponse] = []
