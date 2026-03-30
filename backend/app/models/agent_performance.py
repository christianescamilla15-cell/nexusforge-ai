from datetime import datetime
from pydantic import BaseModel, Field

class AgentPerformance(BaseModel):
    agent_name: str
    workflow_name: str = "all"
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    success_rate: float = 0.0
    avg_quality_score: float = 0.0
    avg_latency_ms: float = 0.0
    avg_tokens: float = 0.0
    avg_cost_usd: float = 0.0
    retry_rate: float = 0.0
    fallback_rate: float = 0.0
    approval_rate: float = 0.0
    operational_score: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
