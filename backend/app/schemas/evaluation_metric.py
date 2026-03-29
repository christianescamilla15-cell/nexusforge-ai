from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvaluationMetricBase(BaseModel):
    evaluation_run_id: UUID
    metric_name: str
    metric_value: Decimal | None = None
    metric_text: str | None = None


class EvaluationMetricCreate(EvaluationMetricBase):
    pass


class EvaluationMetricRead(EvaluationMetricBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
