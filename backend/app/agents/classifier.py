"""ClassifierAgent — classifies document type with Pydantic validation."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent
from app.agents.output_schemas import ClassificationResult

logger = logging.getLogger(__name__)

CATEGORIES = ["legal", "financial", "technical", "medical", "general"]

CLASSIFY_PROMPT = """Classify the following document excerpt into exactly one category.
Categories: {categories}

Respond ONLY with valid JSON (no markdown):
{{"category": "<one of the categories>", "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}}

Document excerpt:
{text}"""


class ClassifierAgent(BaseAgent):
    name = "ClassifierAgent"
    agent_type = "classifier"
    description = "Classifies documents into categories: legal, financial, technical, medical, general."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = input_data.get("text", "")[:500]
        config = config or {}

        if config.get("demo") or not text:
            return AgentResult(
                output={"category": "general", "confidence": 0.5, "reasoning": "Demo mode — no LLM call"},
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        prompt = CLASSIFY_PROMPT.format(categories=", ".join(CATEGORIES), text=text)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Classify the document.")},
            {"role": "user", "content": prompt},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.1, max_tokens=256)
            raw = clean_llm_json(resp.text)
            validated = ClassificationResult.model_validate(raw)
            return AgentResult(
                output=validated.model_dump(),
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("ClassifierAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"category": "general", "confidence": 0.3, "reasoning": f"LLM unavailable: {exc}"},
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )


register_agent("classifier", ClassifierAgent())
