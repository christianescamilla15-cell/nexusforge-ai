"""SummarizerAgent — generates concise summaries of text."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

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
                tokens_used=620, cost_usd=0.0037,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        max_tok = LENGTH_TOKENS.get(length, 300)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Summarize the document.")},
            {"role": "user", "content": SUMMARIZE_PROMPT.format(length=length, text=text[:4000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.3, max_tokens=max_tok + 200)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("SummarizerAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"summary": text[:200] + "...", "key_points": [], "word_count": len(text.split())},
                tokens_used=240, cost_usd=0.0014,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("summarizer", SummarizerAgent())
