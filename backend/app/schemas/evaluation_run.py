from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvaluationRunBase(BaseModel):
    scenario_id: UUID
    workflow_run_id: UUID | None = None
    status: str


class EvaluationRunCreate(EvaluationRunBase):
    pass


class EvaluationRunUpdate(BaseModel):
    status: str | None = None
    workflow_run_id: UUID | None = None
    finished_at: datetime | None = None


class EvaluationRunRead(EvaluationRunBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    started_at: datetime
    finished_at: datetime | None = None
    created_at: datetime
