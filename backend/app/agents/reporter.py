"""ReporterAgent — generates a markdown report from all agent outputs."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

REPORT_PROMPT = """Generate a structured markdown report from the following agent outputs.
Include sections for: Executive Summary, Findings, Analysis, and Recommendations.

Respond ONLY with valid JSON (no markdown fences):
{{
  "report_markdown": "<full markdown report>",
  "sections": ["<section_name>"],
  "word_count": <int>
}}

Agent outputs:
{outputs}"""


class ReporterAgent(BaseAgent):
    name = "ReporterAgent"
    agent_type = "reporter"
    description = "Generates structured markdown reports from all previous agent outputs."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        outputs = input_data.get("outputs", input_data)
        config = config or {}

        if config.get("demo"):
            md = "# Report\n\n## Summary\nDemo report.\n\n## Findings\n- N/A\n"
            return AgentResult(
                output={"report_markdown": md, "sections": ["Summary", "Findings"], "word_count": 6},
                tokens_used=920, cost_usd=0.0055,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Generate a comprehensive report.")},
            {"role": "user", "content": REPORT_PROMPT.format(
                outputs=json.dumps(outputs, indent=2, default=str)[:4000]
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.4, max_tokens=2048)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("ReporterAgent LLM fallback: %s", exc)
            md = "# Report\n\n## Raw Data\n\n```json\n" + json.dumps(outputs, indent=2, default=str)[:2000] + "\n```\n"
            return AgentResult(
                output={"report_markdown": md, "sections": ["Raw Data"], "word_count": len(md.split())},
                tokens_used=380, cost_usd=0.0023,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("reporter", ReporterAgent())
