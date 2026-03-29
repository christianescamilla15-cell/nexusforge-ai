from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkflowStepBase(BaseModel):
    run_id: UUID
    step_order: int
    agent_name: str
    provider_name: str | None = None
    status: str
    input_payload: dict | None = None
    output_payload: dict | None = None
    error_message: str | None = None


class WorkflowStepCreate(WorkflowStepBase):
    pass


class WorkflowStepUpdate(BaseModel):
    status: str | None = None
    output_payload: dict | None = None
    error_message: str | None = None
    finished_at: datetime | None = None
    latency_ms: int | None = None
    tokens_used: int | None = None
    cost_usd: Decimal | None = None
    retry_count: int | None = None
    fallback_triggered: bool | None = None


class WorkflowStepRead(WorkflowStepBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    started_at: datetime | None = None
    finished_at: datetime | None = None
    latency_ms: int | None = None
    tokens_used: int
    cost_usd: Decimal
    retry_count: int
    fallback_triggered: bool
    created_at: datetime
