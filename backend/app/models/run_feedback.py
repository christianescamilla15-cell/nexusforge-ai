from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid

class RunFeedback(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    workflow_name: str = ""
    rating: int = 0  # 1-5
    approved: bool = False
    feedback_type: str = "human"  # human, system, auto
    comments: str = ""
    reviewer: str = "anonymous"
    created_at: datetime = Field(default_factory=datetime.utcnow)
