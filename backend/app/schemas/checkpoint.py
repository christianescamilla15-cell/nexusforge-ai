from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckpointBase(BaseModel):
    run_id: UUID
    step_id: UUID | None = None
    checkpoint_name: str
    state_payload: dict


class CheckpointCreate(CheckpointBase):
    pass


class CheckpointRead(CheckpointBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
