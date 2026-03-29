from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import uuid

class EventType(str, Enum):
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_FAILURE = "agent_failure"
    RETRY = "retry"
    FALLBACK = "fallback"
    CHECKPOINT = "checkpoint"
    RECOVERY = "recovery"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"

class AgentEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    agent_name: str = ""
    event_type: EventType
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
