"""NormalizerAgent — normalizes extracted data into consistent schema."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

NORMALIZE_PROMPT = """Normalize the following raw data records into a consistent schema.
- Standardize date formats to ISO 8601 (YYYY-MM-DD)
- Standardize names to Title Case
- Standardize amounts to numeric with 2 decimal places
- Remove exact duplicates
- Flag near-duplicates

Respond ONLY with valid JSON (no markdown):
{{"normalized_records": [{{...}}], "dedup_count": <int>, "schema_applied": "<description>"}}

Raw data:
{data}"""


class NormalizerAgent(BaseAgent):
    name = "NormalizerAgent"
    agent_type = "normalizer"
    description = "Normalizes extracted data into consistent schema, deduplicates entries, standardizes formats."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        data = input_data.get("data", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not data:
            return AgentResult(
                output={
                    "normalized_records": [
                        {"name": "John Doe", "date": "2026-01-15", "amount": 1500.00},
                        {"name": "Jane Smith", "date": "2026-02-20", "amount": 2300.50},
                    ],
                    "dedup_count": 1,
                    "schema_applied": "Demo — standard name/date/amount schema",
                },
                provider="local", model="none",
            )

        raw = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Normalize data records.")},
            {"role": "user", "content": NORMALIZE_PROMPT.format(data=raw[:3000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.1, max_tokens=2048)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("NormalizerAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"normalized_records": [], "dedup_count": 0, "schema_applied": f"Error: {exc}"},
                provider="local", model="fallback",
            )


register_agent("normalizer", NormalizerAgent())
