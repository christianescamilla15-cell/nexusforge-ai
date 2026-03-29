from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class OperationsRequest(BaseModel):
    """Input for the Enterprise Operations Assistant."""
    message: str = Field(..., description="Customer/internal request message")
    customer_id: Optional[str] = None
    language: str = Field(default="es", description="Response language: es or en")
    priority: str = Field(default="normal", description="Priority: low, normal, high, urgent")

class OperationsResponse(BaseModel):
    """Output from the Enterprise Operations Assistant."""
    run_id: str
    status: str
    intent: str
    customer_name: Optional[str] = None
    actions_taken: List[str] = []
    response_message: str = ""
    documents_consulted: List[str] = []
    crm_updated: bool = False
    notification_sent: bool = False
    processing_time_ms: Optional[float] = None
    agents_used: List[str] = []
    # LLM usage metadata
    provider: str = "none"
    model: str = "none"
    total_tokens: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    llm_used: bool = False
