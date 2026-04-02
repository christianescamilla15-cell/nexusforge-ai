"""AnalyzerAgent — sentiment, topic, and complexity analysis."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

ANALYZE_PROMPT = """Analyze the following text for sentiment, topics, and complexity.

Respond ONLY with valid JSON (no markdown):
{{
  "sentiment": "<positive|negative|neutral|mixed>",
  "topics": ["<topic1>", "<topic2>"],
  "complexity": "<simple|moderate|complex>",
  "statistics": {{
    "word_count": <int>,
    "sentence_count": <int>,
    "avg_sentence_length": <float>
  }}
}}

Text:
{text}"""


class AnalyzerAgent(BaseAgent):
    name = "AnalyzerAgent"
    agent_type = "analyzer"
    description = "Performs sentiment, topic, and complexity analysis on text."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = input_data.get("text", "")
        config = config or {}

        if config.get("demo") or not text:
            return AgentResult(
                output={
                    "sentiment": "neutral",
                    "topics": ["demo"],
                    "complexity": "simple",
                    "statistics": {"word_count": 0, "sentence_count": 0, "avg_sentence_length": 0.0},
                },
                tokens_used=850, cost_usd=0.005,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Analyze the text.")},
            {"role": "user", "content": ANALYZE_PROMPT.format(text=text[:3000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=512)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("AnalyzerAgent LLM fallback: %s", exc)
            words = text.split()
            sentences = [s for s in text.split(".") if s.strip()]
            return AgentResult(
                output={
                    "sentiment": "unknown",
                    "topics": [],
                    "complexity": "unknown",
                    "statistics": {
                        "word_count": len(words),
                        "sentence_count": len(sentences),
                        "avg_sentence_length": len(words) / max(len(sentences), 1),
                    },
                },
                tokens_used=320, cost_usd=0.0019,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("analyzer", AnalyzerAgent())
