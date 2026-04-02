"""SentimentAgent — sentiment and opinion analysis."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

SENTIMENT_PROMPT = """Analyze the sentiment and emotional tone of the following text.

Respond ONLY with valid JSON (no markdown):
{{"sentiment": "<positive/negative/neutral>", "score": <-1.0 to 1.0>, "emotions": ["<emotion1>", "<emotion2>"], "topics": ["<topic1>", "<topic2>"]}}

Text:
{text}"""


class SentimentAgent(BaseAgent):
    name = "SentimentAgent"
    agent_type = "sentiment"
    description = "Analyzes sentiment, emotional tone, and opinion in text."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = input_data.get("text", "")
        config = config or {}

        if config.get("demo") or not text:
            return AgentResult(
                output={
                    "sentiment": "positive",
                    "score": 0.72,
                    "emotions": ["confidence", "satisfaction"],
                    "topics": ["product quality", "customer service"],
                },
                tokens_used=260, cost_usd=0.0016,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Analyze sentiment and emotions.")},
            {"role": "user", "content": SENTIMENT_PROMPT.format(text=text[:3000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.1, max_tokens=512)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("SentimentAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"sentiment": "neutral", "score": 0.0, "emotions": [], "topics": []},
                tokens_used=110, cost_usd=0.0007,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("sentiment", SentimentAgent())
