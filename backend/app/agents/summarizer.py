"""SummarizerAgent — generates concise summaries with Pydantic validation."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent
from app.agents.output_schemas import SummaryResult

logger = logging.getLogger(__name__)

LENGTH_TOKENS = {"short": 100, "medium": 300, "long": 600}

SUMMARIZE_PROMPT = """Summarize the following text. Target length: {length}.

Respond ONLY with valid JSON (no markdown):
{{"summary": "<concise summary>", "key_points": ["<point1>", "<point2>"], "word_count": <int>}}

Text:
{text}"""


class SummarizerAgent(BaseAgent):
    name = "SummarizerAgent"
    agent_type = "summarizer"
    description = "Generates concise summaries with configurable length (short/medium/long)."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = input_data.get("text", "")
        config = config or {}
        length = config.get("length", "medium")

        if config.get("demo") or not text:
            return AgentResult(
                output={"summary": "Demo summary.", "key_points": ["Point A", "Point B"], "word_count": 2},
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        max_tok = LENGTH_TOKENS.get(length, 300)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Summarize the document.")},
            {"role": "user", "content": SUMMARIZE_PROMPT.format(length=length, text=text[:4000])},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.3, max_tokens=max_tok + 200)
            raw = clean_llm_json(resp.text)
            validated = SummaryResult.model_validate(raw)
            return AgentResult(
                output=validated.model_dump(),
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("SummarizerAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"summary": text[:200] + "...", "key_points": [], "word_count": len(text.split())},
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )


register_agent("summarizer", SummarizerAgent())
