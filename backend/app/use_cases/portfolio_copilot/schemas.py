from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class PortfolioCopilotInput(BaseModel):
    question: str = Field(..., description="Question about the portfolio")
    language: str = Field(default="es")
    context: Optional[str] = None

class PortfolioCopilotFinalOutput(BaseModel):
    run_id: str
    status: str
    question_type: str = ""
    recommended_project: Optional[str] = None
    reasoning: str = ""
    supporting_projects: List[str] = []
    related_skills: List[str] = []
    final_answer: str = ""
    requires_human_review: bool = False
    agents_used: List[str] = []
    actions_taken: List[str] = []
    processing_time_ms: Optional[float] = None
    audit_summary: str = ""
    # LLM usage metadata
    provider: str = "none"
    model: str = "none"
    total_tokens: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    llm_used: bool = False
