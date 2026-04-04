"""ReporterAgent — structured reports with multi-format output."""

import json
import logging
import time

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

REPORT_PROMPT = """Generate a structured professional report from the following agent outputs.

Required sections:
1. Executive Summary (2-3 sentences)
2. Key Findings (bullet points)
3. Detailed Analysis (per-agent breakdown)
4. Recommendations (actionable next steps)
5. Metadata (processing time, agents used, confidence)

Respond ONLY with valid JSON (no markdown fences):
{{
  "title": "<report title>",
  "executive_summary": "<2-3 sentence overview>",
  "key_findings": ["<finding1>", "<finding2>"],
  "analysis": [
    {{"section": "<agent/topic>", "content": "<detailed markdown>", "confidence": <0-1>}}
  ],
  "recommendations": ["<rec1>", "<rec2>"],
  "report_markdown": "<full rendered markdown report>",
  "word_count": <int>,
  "generated_at": "{timestamp}"
}}

Agent outputs:
{outputs}"""


class ReporterAgent(BaseAgent):
    name = "ReporterAgent"
    agent_type = "reporter"
    description = "Generates structured professional reports with executive summary, findings, and recommendations."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        outputs = input_data.get("outputs", input_data)
        config = config or {}
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if config.get("demo"):
            md = "# Report\n\n## Executive Summary\nDemo report generated.\n\n## Key Findings\n- Finding 1\n\n## Recommendations\n- Review data\n"
            return AgentResult(
                output={
                    "title": "Demo Report",
                    "executive_summary": "Demo report generated.",
                    "key_findings": ["Finding 1"],
                    "analysis": [],
                    "recommendations": ["Review data"],
                    "report_markdown": md,
                    "word_count": 12,
                    "generated_at": ts,
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt(
                "Generate comprehensive professional reports."
            )},
            {"role": "user", "content": REPORT_PROMPT.format(
                outputs=json.dumps(outputs, indent=2, default=str)[:4000],
                timestamp=ts,
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.4, max_tokens=2048)
            parsed = clean_llm_json(resp.text)

            # Ensure generated_at is set
            parsed.setdefault("generated_at", ts)

            # Build markdown if LLM didn't provide it
            if not parsed.get("report_markdown"):
                parsed["report_markdown"] = self._build_markdown(parsed)

            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("ReporterAgent LLM fallback: %s", exc)
            # Fallback: generate a basic structured report from raw data
            md = self._fallback_report(outputs, ts)
            return AgentResult(
                output={
                    "title": "Automation Report",
                    "executive_summary": "Report generated from raw agent outputs (LLM unavailable).",
                    "key_findings": [],
                    "analysis": [],
                    "recommendations": [],
                    "report_markdown": md,
                    "word_count": len(md.split()),
                    "generated_at": ts,
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )

    @staticmethod
    def _build_markdown(parsed: dict) -> str:
        """Build markdown from structured sections."""
        lines = [f"# {parsed.get('title', 'Report')}", ""]
        if parsed.get("executive_summary"):
            lines += ["## Executive Summary", "", parsed["executive_summary"], ""]
        if parsed.get("key_findings"):
            lines += ["## Key Findings", ""]
            for f in parsed["key_findings"]:
                lines.append(f"- {f}")
            lines.append("")
        if parsed.get("analysis"):
            lines += ["## Detailed Analysis", ""]
            for a in parsed["analysis"]:
                lines += [f"### {a.get('section', 'Section')}", "", a.get("content", ""), ""]
        if parsed.get("recommendations"):
            lines += ["## Recommendations", ""]
            for r in parsed["recommendations"]:
                lines.append(f"- {r}")
            lines.append("")
        lines += [f"---", f"*Generated: {parsed.get('generated_at', '')}*"]
        return "\n".join(lines)

    @staticmethod
    def _fallback_report(outputs: dict, ts: str) -> str:
        """Generate a basic report when LLM is unavailable."""
        lines = ["# Automation Report", "", "## Raw Agent Outputs", ""]
        if isinstance(outputs, dict):
            for key, val in outputs.items():
                if key.startswith("_"):
                    continue
                lines += [f"### {key}", "", "```json", json.dumps(val, indent=2, default=str)[:800], "```", ""]
        else:
            lines += ["```json", json.dumps(outputs, indent=2, default=str)[:2000], "```"]
        lines += ["", "---", f"*Generated: {ts} (fallback mode)*"]
        return "\n".join(lines)


register_agent("reporter", ReporterAgent())
