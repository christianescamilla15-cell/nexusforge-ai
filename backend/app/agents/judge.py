"""JudgeAgent — evaluates consensus between multiple agents and selects the best output."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

_JUDGE_PROMPT = """\
You are an impartial judge evaluating outputs from multiple agents that analyzed the same task.

Task input:
{task_input}

Agent outputs:
{outputs}

Evaluate all outputs and respond ONLY with valid JSON (no markdown):
{{
  "best_agent": "<agent_type of the best output>",
  "best_output": {{<the best output, copied verbatim>}},
  "ranking": [
    {{"rank": 1, "agent": "<agent_type>", "quality": <0-100>, "reason": "<brief>"}},
    {{"rank": 2, "agent": "<agent_type>", "quality": <0-100>, "reason": "<brief>"}}
  ],
  "consensus": "<synthesized conclusion combining the best insights>",
  "confidence": <0-100>
}}"""


class JudgeAgent(BaseAgent):
    name = "JudgeAgent"
    agent_type = "judge"
    description = "Evaluates consensus between multiple agents and selects the best output."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        task_input = self._extract_text(input_data)
        outputs = input_data.get("agent_outputs", {})

        if not outputs:
            return AgentResult(
                output={"error": "JudgeAgent requires 'agent_outputs' dict in input_data"},
                provider="local", model="none",
            )

        outputs_str = json.dumps(outputs, indent=2, default=str)
        messages = [
            {"role": "system", "content": "You are a strict but fair judge of AI agent outputs. Always return valid JSON."},
            {"role": "user", "content": _JUDGE_PROMPT.format(
                task_input=task_input[:2000],
                outputs=outputs_str[:4000],
            )},
        ]

        response = await self._resilient_llm_call(messages, temperature=0.1, max_tokens=1024)
        result = clean_llm_json(response.text)

        return AgentResult(
            output=result,
            tokens_used=response.tokens_input + response.tokens_output,
            cost_usd=response.cost_usd,
            provider=response.provider,
            model=response.model,
        )


register_agent("judge", JudgeAgent())
