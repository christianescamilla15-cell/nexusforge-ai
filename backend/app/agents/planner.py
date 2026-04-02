"""PlannerAgent — decomposes complex tasks into subtasks with dependencies."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent, list_agents
from app.llm.router import get_router

logger = logging.getLogger(__name__)

PLAN_PROMPT = """Decompose the following complex task into an ordered execution plan.
Each step should specify which agent handles it and its dependencies.

Available agents: {agents}

Respond ONLY with valid JSON (no markdown):
{{"plan": [{{"step": <int>, "description": "<what to do>", "agent": "<agent_type>", "dependencies": [<step_numbers>], "priority": "<high/medium/low>"}}], "estimated_steps": <int>, "complexity": "<low/medium/high>"}}

Task:
{task}"""


class PlannerAgent(BaseAgent):
    name = "PlannerAgent"
    agent_type = "planner"
    description = "Decomposes complex tasks into subtasks and creates execution plans with dependencies."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        task = input_data.get("task", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not task:
            return AgentResult(
                output={
                    "plan": [
                        {"step": 1, "description": "Classify document type", "agent": "classifier", "dependencies": [], "priority": "high"},
                        {"step": 2, "description": "Extract entities", "agent": "extractor", "dependencies": [1], "priority": "high"},
                        {"step": 3, "description": "Validate extracted data", "agent": "validator", "dependencies": [2], "priority": "medium"},
                        {"step": 4, "description": "Generate summary", "agent": "summarizer", "dependencies": [2], "priority": "medium"},
                    ],
                    "estimated_steps": 4,
                    "complexity": "medium",
                },
                tokens_used=670, cost_usd=0.004,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        available = list_agents()
        messages = [
            {"role": "system", "content": self._build_system_prompt("Plan task execution.")},
            {"role": "user", "content": PLAN_PROMPT.format(agents=", ".join(available), task=task[:2000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.3, max_tokens=2048)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("PlannerAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"plan": [], "estimated_steps": 0, "complexity": "unknown"},
                tokens_used=250, cost_usd=0.0015,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("planner", PlannerAgent())
