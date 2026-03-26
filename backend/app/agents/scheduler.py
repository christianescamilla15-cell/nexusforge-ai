"""SchedulerAgent — suggests optimal execution scheduling."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

SCHEDULE_PROMPT = """Given the following tasks and their requirements, suggest an optimal execution schedule.
Consider dependencies, resource constraints, and parallelization opportunities.

Respond ONLY with valid JSON (no markdown):
{{"recommended_schedule": "<description of schedule>", "estimated_duration": "<total time>", "resource_usage": "<cpu/memory estimate>", "priority_order": ["<task1>", "<task2>"]}}

Tasks:
{tasks}"""


class SchedulerAgent(BaseAgent):
    name = "SchedulerAgent"
    agent_type = "scheduler"
    description = "Suggests optimal execution scheduling for task pipelines."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        tasks = input_data.get("tasks", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not tasks:
            return AgentResult(
                output={
                    "recommended_schedule": "Parallel Phase 1 (classify + OCR) -> Sequential Phase 2 (extract) -> Parallel Phase 3 (validate + summarize)",
                    "estimated_duration": "4.2 seconds",
                    "resource_usage": "CPU: 35%, Memory: 128MB peak",
                    "priority_order": ["classifier", "ocr", "extractor", "validator", "summarizer"],
                },
                provider="local", model="none",
            )

        raw = json.dumps(tasks) if isinstance(tasks, (dict, list)) else str(tasks)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Optimize task scheduling.")},
            {"role": "user", "content": SCHEDULE_PROMPT.format(tasks=raw[:3000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("SchedulerAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"recommended_schedule": "Sequential", "estimated_duration": "unknown", "resource_usage": "unknown", "priority_order": []},
                provider="local", model="fallback",
            )


register_agent("scheduler", SchedulerAgent())
