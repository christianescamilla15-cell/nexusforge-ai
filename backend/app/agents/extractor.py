"""ExtractorAgent — extracts named entities from text."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """Extract all named entities from the text below.
Entity types to find: person, organization, date, amount, location.

Respond ONLY with valid JSON (no markdown):
{{"entities": [{{"type": "<entity_type>", "value": "<extracted value>", "context": "<sentence where found>"}}]}}

Text:
{text}"""


class ExtractorAgent(BaseAgent):
    name = "ExtractorAgent"
    agent_type = "extractor"
    description = "Extracts named entities (people, orgs, dates, amounts, locations) from text."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = input_data.get("text", "")
        config = config or {}

        if config.get("demo") or not text:
            return AgentResult(
                output={"entities": [
                    {"type": "person", "value": "John Doe", "context": "Demo entity"},
                    {"type": "organization", "value": "Acme Corp", "context": "Demo entity"},
                ]},
                provider="local", model="none",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Extract named entities.")},
            {"role": "user", "content": EXTRACT_PROMPT.format(text=text[:3000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.1, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("ExtractorAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"entities": [], "error": str(exc)},
                provider="local", model="fallback",
            )


register_agent("extractor", ExtractorAgent())
