from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentEventBase(BaseModel):
    run_id: UUID
    step_id: UUID | None = None
    agent_name: str
    event_type: str
    event_message: str | None = None
    metadata: dict | None = None


class AgentEventCreate(AgentEventBase):
    pass


class AgentEventRead(AgentEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
