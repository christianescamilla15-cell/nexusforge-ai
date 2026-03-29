from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
import uuid

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRIED = "retried"

class WorkflowStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    step_index: int
    agent_name: str
    status: StepStatus = StepStatus.PENDING
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    latency_ms: Optional[float] = None
    provider_used: str = ""
    retry_count: int = 0
    error_message: Optional[str] = None
    output_summary: Optional[str] = None
