"""ClassifierAgent — classifies document type using LLM."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

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

        # Fallback / demo mode
        if config.get("demo") or not text:
            return AgentResult(
                output={"category": "general", "confidence": 0.5, "reasoning": "Demo mode — no LLM call"},
                provider="local", model="none",
            )

        prompt = CLASSIFY_PROMPT.format(categories=", ".join(CATEGORIES), text=text)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Classify the document.")},
            {"role": "user", "content": prompt},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.1, max_tokens=256)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("ClassifierAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"category": "general", "confidence": 0.3, "reasoning": f"LLM unavailable: {exc}"},
                provider="local", model="fallback",
            )


# Self-register
register_agent("classifier", ClassifierAgent())
