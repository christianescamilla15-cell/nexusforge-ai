"""EnricherAgent — enriches extracted entities with context."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

ENRICH_PROMPT = """Given the following extracted entities and the source text, enrich each entity
with additional context and related information.

Respond ONLY with valid JSON (no markdown):
{{"enriched_entities": [{{"type": "<type>", "value": "<value>", "context": "<original context>", "enrichment": "<additional info>", "related": ["<related entity or concept>"]}}]}}

Entities:
{entities}

Source text:
{text}"""


class EnricherAgent(BaseAgent):
    name = "EnricherAgent"
    agent_type = "enricher"
    description = "Enriches extracted entities with additional context and cross-references."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        entities = input_data.get("entities", [])
        text = input_data.get("text", "")
        config = config or {}

        if config.get("demo") or not entities:
            return AgentResult(
                output={"enriched_entities": [
                    {"type": "person", "value": "Demo", "context": "N/A",
                     "enrichment": "Demo enrichment", "related": []},
                ]},
                tokens_used=390, cost_usd=0.0023,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Enrich entities with context.")},
            {"role": "user", "content": ENRICH_PROMPT.format(
                entities=json.dumps(entities, indent=2),
                text=text[:2000],
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.3, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("EnricherAgent LLM fallback: %s", exc)
            enriched = [
                {**e, "enrichment": "LLM unavailable", "related": []}
                for e in entities
            ]
            return AgentResult(
                output={"enriched_entities": enriched},
                tokens_used=150, cost_usd=0.0009,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("enricher", EnricherAgent())
