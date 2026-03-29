from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvaluationScenarioBase(BaseModel):
    scenario_name: str
    workflow_name: str
    input_payload: dict
    expected_capabilities: dict | None = None
    expected_constraints: dict | None = None
    tags: dict | None = None


class EvaluationScenarioCreate(EvaluationScenarioBase):
    pass


class EvaluationScenarioRead(EvaluationScenarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
