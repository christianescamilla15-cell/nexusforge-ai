from pydantic import BaseModel, Field

class RunMetrics(BaseModel):
    run_id: str
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_latency_ms: float = 0.0
    avg_step_latency_ms: float = 0.0
    total_cost: float = 0.0
    retry_count: int = 0
    fallback_count: int = 0
    success_rate: float = 0.0
    agents_used: int = 0
    topology: str = ""
