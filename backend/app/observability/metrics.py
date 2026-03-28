"""Custom metrics for agent execution, token usage, and cost tracking."""
from dataclasses import dataclass, field
from datetime import datetime
import time

@dataclass
class AgentMetric:
    agent_type: str
    duration_ms: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    success: bool = True
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

class MetricsCollector:
    def __init__(self):
        self._metrics: list[AgentMetric] = []

    def record(self, metric: AgentMetric):
        self._metrics.append(metric)

    def get_summary(self):
        if not self._metrics:
            return {'total_requests': 0}
        total = len(self._metrics)
        success = sum(1 for m in self._metrics if m.success)
        return {
            'total_requests': total,
            'success_rate': round(success / total, 2),
            'avg_duration_ms': round(sum(m.duration_ms for m in self._metrics) / total),
            'total_tokens': sum(m.tokens_used for m in self._metrics),
            'total_cost_usd': round(sum(m.cost_usd for m in self._metrics), 4),
            'by_agent': self._by_agent(),
        }

    def _by_agent(self):
        agents = {}
        for m in self._metrics:
            if m.agent_type not in agents:
                agents[m.agent_type] = {'count': 0, 'tokens': 0, 'cost': 0}
            agents[m.agent_type]['count'] += 1
            agents[m.agent_type]['tokens'] += m.tokens_used
            agents[m.agent_type]['cost'] += m.cost_usd
        return agents

collector = MetricsCollector()
