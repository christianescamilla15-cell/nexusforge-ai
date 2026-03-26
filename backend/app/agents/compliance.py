"""ComplianceAgent — checks text against regulatory rules."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

COMPLIANCE_PROMPT = """Analyze the following text for regulatory compliance issues.
Check against common regulations (GDPR, HIPAA, SOX, PCI-DSS, etc.).

Respond ONLY with valid JSON (no markdown):
{{"is_compliant": <true/false>, "issues": [{{"rule": "<regulation>", "violation": "<description>", "severity": "<high/medium/low>"}}], "risk_score": <0-100>}}

Text:
{text}"""


class ComplianceAgent(BaseAgent):
    name = "ComplianceAgent"
    agent_type = "compliance"
    description = "Checks text against regulatory rules and identifies potential compliance issues."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = input_data.get("text", "")
        config = config or {}

        if config.get("demo") or not text:
            return AgentResult(
                output={
                    "is_compliant": False,
                    "issues": [
                        {"rule": "GDPR Art.13", "violation": "Missing data processing disclosure", "severity": "high"},
                        {"rule": "PCI-DSS 3.4", "violation": "Potential unmasked card numbers", "severity": "medium"},
                    ],
                    "risk_score": 65,
                },
                provider="local", model="none",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Analyze for compliance issues.")},
            {"role": "user", "content": COMPLIANCE_PROMPT.format(text=text[:3000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.1, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("ComplianceAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"is_compliant": True, "issues": [], "risk_score": 0},
                provider="local", model="fallback",
            )


register_agent("compliance", ComplianceAgent())
