from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum
import uuid

class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

class WorkflowRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_name: str
    topology: str = "sequential"
    status: RunStatus = RunStatus.PENDING
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    total_latency_ms: Optional[float] = None
    total_cost: float = 0.0
    total_tokens: int = 0
    provider_used: str = ""
    model_used: str = ""
    agent_count: int = 0
    step_count: int = 0
    retry_count: int = 0
    fallback_used: bool = False
    metadata: dict = Field(default_factory=dict)
