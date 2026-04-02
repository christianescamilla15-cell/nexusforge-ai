"""RepairAgent — self-healing agent that diagnoses and fixes failed steps."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

REPAIR_PROMPT = """A workflow step has failed. Analyze the error and suggest a fix.

Step name: {step_name}
Step type: {step_type}
Error message: {error}
Step config: {config}

Respond ONLY with valid JSON (no markdown):
{{
  "diagnosis": "<what went wrong>",
  "fix_type": "<retry|reconfigure|skip|escalate>",
  "suggested_config": {{}},
  "can_auto_fix": <true|false>
}}"""


class RepairAgent(BaseAgent):
    name = "RepairAgent"
    agent_type = "repair"
    description = "Analyzes failed workflow steps and suggests fixes for self-healing."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        error = input_data.get("error", "Unknown error")
        step_name = input_data.get("step_name", "unknown")
        step_type = input_data.get("step_type", "unknown")
        step_config = input_data.get("step_config", {})
        config = config or {}

        if config.get("demo"):
            return AgentResult(
                output={
                    "diagnosis": "Demo mode — no real error",
                    "fix_type": "retry",
                    "suggested_config": {},
                    "can_auto_fix": True,
                },
                tokens_used=310, cost_usd=0.0018,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Diagnose and fix the failed step.")},
            {"role": "user", "content": REPAIR_PROMPT.format(
                step_name=step_name,
                step_type=step_type,
                error=str(error)[:500],
                config=json.dumps(step_config, default=str)[:500],
            )},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=512)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("RepairAgent LLM fallback: %s", exc)
            # Heuristic-based repair without LLM
            fix_type = "retry"
            can_auto = True
            if "timeout" in str(error).lower():
                diagnosis = "Request timed out"
            elif "rate" in str(error).lower():
                diagnosis = "Rate limit hit"
                fix_type = "retry"
            elif "auth" in str(error).lower() or "401" in str(error):
                diagnosis = "Authentication failure"
                fix_type = "escalate"
                can_auto = False
            else:
                diagnosis = f"Unknown error: {error}"
                fix_type = "retry"

            return AgentResult(
                output={
                    "diagnosis": diagnosis,
                    "fix_type": fix_type,
                    "suggested_config": step_config,
                    "can_auto_fix": can_auto,
                },
                tokens_used=175, cost_usd=0.001,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("repair", RepairAgent())
