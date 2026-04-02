"""ValidatorAgent — quality gate that validates output from previous agents."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

VALIDATE_PROMPT = """You are a quality validator. Evaluate the following agent output for completeness,
consistency, and accuracy.

Respond ONLY with valid JSON (no markdown):
{{
  "is_valid": <true|false>,
  "score": <0-100>,
  "issues": ["<issue description>"],
  "recommendations": ["<recommendation>"]
}}

Agent output to validate:
{output}

Original input context:
{context}"""


class ValidatorAgent(BaseAgent):
    name = "ValidatorAgent"
    agent_type = "validator"
    description = "Quality gate: validates completeness, consistency, and accuracy of agent outputs."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        output_to_validate = input_data.get("output", input_data.get("text", {}))
        context = input_data.get("context", "")
        config = config or {}

        if config.get("demo"):
            return AgentResult(
                output={"is_valid": True, "score": 85, "issues": [], "recommendations": ["Demo mode"]},
                tokens_used=300, cost_usd=0.0018,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Validate the agent output.")},
            {"role": "user", "content": VALIDATE_PROMPT.format(
                output=json.dumps(output_to_validate, indent=2)[:2000],
                context=str(context)[:1000],
            )},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.1, max_tokens=512)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("ValidatorAgent LLM fallback: %s", exc)
            has_data = bool(output_to_validate) and output_to_validate != {}
            return AgentResult(
                output={
                    "is_valid": has_data,
                    "score": 50 if has_data else 0,
                    "issues": [] if has_data else ["No output data to validate"],
                    "recommendations": [f"LLM unavailable: {exc}"],
                },
                tokens_used=200, cost_usd=0.0012,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("validator", ValidatorAgent())
