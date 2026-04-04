"""SchedulerAgent — cron expression understanding + NLP scheduling + optimization."""

import json
import logging
import re
from datetime import datetime, timedelta

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

# Human-readable cron descriptions
_CRON_DESCRIPTIONS = {
    "* * * * *": "Every minute",
    "*/5 * * * *": "Every 5 minutes",
    "*/15 * * * *": "Every 15 minutes",
    "*/30 * * * *": "Every 30 minutes",
    "0 * * * *": "Every hour",
    "0 */2 * * *": "Every 2 hours",
    "0 */6 * * *": "Every 6 hours",
    "0 0 * * *": "Daily at midnight",
    "0 8 * * *": "Daily at 8:00 AM",
    "0 9 * * 1-5": "Weekdays at 9:00 AM",
    "0 9 * * 1": "Every Monday at 9:00 AM",
    "0 8 1 * *": "First day of every month at 8:00 AM",
    "0 0 * * 0": "Every Sunday at midnight",
}

# NLP → cron mapping for common Spanish/English patterns
_NLP_PATTERNS = [
    (r"(?i)cada\s+(\d+)\s+minutos?|every\s+(\d+)\s+minutes?", lambda m: f"*/{m.group(1) or m.group(2)} * * * *"),
    (r"(?i)cada\s+hora|every\s+hour", lambda m: "0 * * * *"),
    (r"(?i)cada\s+d[ií]a\s+a\s+las?\s+(\d{1,2})|daily\s+at\s+(\d{1,2})", lambda m: f"0 {m.group(1) or m.group(2)} * * *"),
    (r"(?i)cada\s+lunes|every\s+monday", lambda m: "0 9 * * 1"),
    (r"(?i)cada\s+martes|every\s+tuesday", lambda m: "0 9 * * 2"),
    (r"(?i)cada\s+mi[eé]rcoles|every\s+wednesday", lambda m: "0 9 * * 3"),
    (r"(?i)cada\s+jueves|every\s+thursday", lambda m: "0 9 * * 4"),
    (r"(?i)cada\s+viernes|every\s+friday", lambda m: "0 9 * * 5"),
    (r"(?i)entre\s+semana|weekdays", lambda m: "0 9 * * 1-5"),
    (r"(?i)cada\s+semana|every\s+week|weekly", lambda m: "0 9 * * 1"),
    (r"(?i)cada\s+mes|every\s+month|monthly", lambda m: "0 8 1 * *"),
    (r"(?i)diario|diariamente|daily", lambda m: "0 8 * * *"),
]

SCHEDULE_PROMPT = """Given the following tasks and scheduling requirements, create an optimal execution schedule.
Consider dependencies, resource constraints, and parallelization.

If the user describes a schedule in natural language, convert it to a cron expression.

Respond ONLY with valid JSON (no markdown):
{{
  "recommended_schedule": "<description>",
  "cron_expression": "<cron or null>",
  "cron_human_readable": "<human description>",
  "estimated_duration": "<total time>",
  "resource_usage": "<estimate>",
  "priority_order": ["<task1>"],
  "parallelizable_groups": [["<tasks that can run together>"]]
}}

Tasks/Schedule request:
{tasks}"""


def _parse_nlp_schedule(text: str) -> dict | None:
    """Try to parse natural language scheduling to cron. Returns dict or None."""
    for pattern, cron_fn in _NLP_PATTERNS:
        match = re.search(pattern, text)
        if match:
            cron = cron_fn(match)
            description = _CRON_DESCRIPTIONS.get(cron, f"Custom: {cron}")
            return {
                "cron_expression": cron,
                "cron_human_readable": description,
                "_parsed_from": match.group(0),
            }
    return None


class SchedulerAgent(BaseAgent):
    name = "SchedulerAgent"
    agent_type = "scheduler"
    description = "Schedule optimization with NLP date parsing and cron expression generation."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        tasks = input_data.get("tasks", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not tasks:
            return AgentResult(
                output={
                    "recommended_schedule": "Parallel Phase 1 (classify + OCR) → Sequential Phase 2 (extract) → Parallel Phase 3 (validate + summarize)",
                    "cron_expression": None,
                    "cron_human_readable": None,
                    "estimated_duration": "4.2 seconds",
                    "resource_usage": "CPU: 35%, Memory: 128MB peak",
                    "priority_order": ["classifier", "ocr", "extractor", "validator", "summarizer"],
                    "parallelizable_groups": [["classifier", "ocr"], ["extractor"], ["validator", "summarizer"]],
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        task_text = json.dumps(tasks) if isinstance(tasks, (dict, list)) else str(tasks)

        # Layer 1: NLP cron parsing (instant, $0)
        nlp_result = _parse_nlp_schedule(task_text)
        if nlp_result:
            return AgentResult(
                output={
                    "recommended_schedule": f"Recurring: {nlp_result['cron_human_readable']}",
                    **nlp_result,
                    "estimated_duration": "Recurring",
                    "resource_usage": "Varies per execution",
                    "priority_order": [],
                    "parallelizable_groups": [],
                    "_scheduling_method": "nlp_cron",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="nlp-cron-parser",
            )

        # Layer 2: LLM for complex scheduling
        messages = [
            {"role": "system", "content": self._build_system_prompt("Optimize task scheduling and create cron expressions.")},
            {"role": "user", "content": SCHEDULE_PROMPT.format(tasks=task_text[:3000])},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.2, max_tokens=1024)
            parsed = json.loads(resp.text)
            parsed["_scheduling_method"] = "llm"
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("SchedulerAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "recommended_schedule": "Sequential execution (LLM unavailable)",
                    "cron_expression": None,
                    "cron_human_readable": None,
                    "estimated_duration": "unknown",
                    "resource_usage": "unknown",
                    "priority_order": [],
                    "parallelizable_groups": [],
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )


register_agent("scheduler", SchedulerAgent())
