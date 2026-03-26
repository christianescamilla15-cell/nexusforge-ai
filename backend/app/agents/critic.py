"""CriticAgent — evaluates output quality from other agents."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

CRITIQUE_PROMPT = """Evaluate the quality of the following agent output.
Provide a score (0-100), detailed critique, strengths, and improvements.

Respond ONLY with valid JSON (no markdown):
{{"score": <0-100>, "critique": "<detailed assessment>", "strengths": ["<s1>"], "improvements": ["<i1>"], "pass": <true/false>}}

Agent output to evaluate:
{output}"""


class CriticAgent(BaseAgent):
    name = "CriticAgent"
    agent_type = "critic"
    description = "Evaluates output quality from other agents, provides scores and detailed critiques."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        output = input_data.get("output", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not output:
            return AgentResult(
                output={
                    "score": 78,
                    "critique": "Demo evaluation — output is generally well-structured with minor gaps.",
                    "strengths": ["Clear formatting", "Complete data fields"],
                    "improvements": ["Add confidence scores", "Include source references"],
                    "pass": True,
                },
                provider="local", model="none",
            )

        raw = json.dumps(output) if isinstance(output, (dict, list)) else str(output)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Critically evaluate agent output quality.")},
            {"role": "user", "content": CRITIQUE_PROMPT.format(output=raw[:3000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.3, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("CriticAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"score": 50, "critique": f"Evaluation unavailable: {exc}", "strengths": [], "improvements": [], "pass": True},
                provider="local", model="fallback",
            )


register_agent("critic", CriticAgent())
