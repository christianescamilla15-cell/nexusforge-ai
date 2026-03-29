from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkflowRunBase(BaseModel):
    workflow_name: str
    topology: str
    status: str
    input_payload: dict | None = None
    output_payload: dict | None = None


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRunUpdate(BaseModel):
    status: str | None = None
    output_payload: dict | None = None
    finished_at: datetime | None = None
    total_latency_ms: int | None = None
    total_tokens: int | None = None
    total_cost_usd: Decimal | None = None
    fallback_used: bool | None = None
    retry_count: int | None = None


class WorkflowRunRead(WorkflowRunBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    started_at: datetime
    finished_at: datetime | None = None
    total_latency_ms: int | None = None
    total_tokens: int
    total_cost_usd: Decimal
    fallback_used: bool
    retry_count: int
    created_at: datetime
