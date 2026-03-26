from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class AgentResponse(BaseModel):
    id: UUID
    name: str
    agent_type: str
    description: Optional[str]
    config: dict
    tools: list[str]
    status: str
    created_at: datetime
