"""ValidatorAgent — quality gate with Pydantic schema validation."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent
from app.agents.output_schemas import ValidationResult

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

        # Layer 1: Pydantic structural pre-validation (instant, free)
        if isinstance(output_to_validate, dict):
            structural_issues = self._structural_check(output_to_validate)
        else:
            structural_issues = []

        if config.get("demo"):
            return AgentResult(
                output={"is_valid": True, "score": 85, "issues": [], "recommendations": ["Demo mode"]},
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        # Layer 2: LLM semantic validation
        messages = [
            {"role": "system", "content": self._build_system_prompt("Validate the agent output.")},
            {"role": "user", "content": VALIDATE_PROMPT.format(
                output=json.dumps(output_to_validate, indent=2)[:2000],
                context=str(context)[:1000],
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.1, max_tokens=512)
            raw = clean_llm_json(resp.text)
            validated = ValidationResult.model_validate(raw)
            result = validated.model_dump()
            # Merge structural issues from Layer 1
            if structural_issues:
                result["issues"] = structural_issues + result["issues"]
                result["score"] = max(0, result["score"] - len(structural_issues) * 10)
                result["is_valid"] = result["score"] >= 50
            return AgentResult(
                output=result,
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
                    "is_valid": has_data and not structural_issues,
                    "score": 50 if has_data else 0,
                    "issues": structural_issues or ([] if has_data else ["No output data to validate"]),
                    "recommendations": [f"LLM unavailable: {exc}"],
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )

    @staticmethod
    def _structural_check(data: dict) -> list[str]:
        """Layer 1: deterministic checks — free, instant, no LLM needed."""
        issues = []
        if not data:
            issues.append("Output is empty")
        for key, val in data.items():
            if val is None:
                issues.append(f"Field '{key}' is null")
            elif isinstance(val, str) and not val.strip():
                issues.append(f"Field '{key}' is empty string")
            elif isinstance(val, list) and len(val) == 0:
                issues.append(f"Field '{key}' is empty list")
        return issues


register_agent("validator", ValidatorAgent())
