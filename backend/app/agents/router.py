"""RouterAgent — intelligent task routing based on content analysis."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent, list_agents
from app.llm.router import get_router

logger = logging.getLogger(__name__)

ROUTE_PROMPT = """Analyze the following task and determine which agent(s) should handle it.

Available agents: {agents}

Respond ONLY with valid JSON (no markdown):
{{"recommended_agents": ["<agent_type1>", "<agent_type2>"], "reasoning": "<explanation>", "confidence": <0.0-1.0>}}

Task:
{task}"""


class RouterAgent(BaseAgent):
    name = "RouterAgent"
    agent_type = "router_agent"
    description = "Intelligent task routing — determines which agent(s) should handle a given task."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        task = input_data.get("task", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not task:
            return AgentResult(
                output={
                    "recommended_agents": ["classifier", "extractor", "summarizer"],
                    "reasoning": "Demo mode — standard document processing pipeline",
                    "confidence": 0.85,
                },
                tokens_used=290, cost_usd=0.0017,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        available = list_agents()
        messages = [
            {"role": "system", "content": self._build_system_prompt("Route tasks to appropriate agents.")},
            {"role": "user", "content": ROUTE_PROMPT.format(agents=", ".join(available), task=task[:2000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=512)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("RouterAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"recommended_agents": ["classifier"], "reasoning": f"Fallback: {exc}", "confidence": 0.3},
                tokens_used=130, cost_usd=0.0008,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("router_agent", RouterAgent())
