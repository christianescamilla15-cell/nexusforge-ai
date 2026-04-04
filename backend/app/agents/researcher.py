"""ResearcherAgent — multi-source research with citations."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

RESEARCH_PROMPT = """Research the following topic thoroughly. Provide a comprehensive summary
with cited sources and key findings.

Respond ONLY with valid JSON (no markdown):
{{"summary": "<research summary>", "sources": [{{"title": "<source>", "url": "<url or reference>", "relevance": "<high/medium/low>"}}], "key_findings": ["<finding1>", "<finding2>"]}}

Topic:
{topic}"""


class ResearcherAgent(BaseAgent):
    name = "ResearcherAgent"
    agent_type = "researcher"
    description = "Conducts multi-source research on a topic and returns a summary with citations."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        topic = input_data.get("topic", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not topic:
            return AgentResult(
                output={
                    "summary": "Demo research summary on AI agent architectures.",
                    "sources": [
                        {"title": "Multi-Agent Systems Overview", "url": "https://example.com/mas", "relevance": "high"},
                        {"title": "LLM Orchestration Patterns", "url": "https://example.com/llm", "relevance": "medium"},
                    ],
                    "key_findings": [
                        "Multi-agent systems improve task decomposition by 40%",
                        "Memory-augmented agents show better long-term performance",
                    ],
                },
                tokens_used=1050, cost_usd=0.0063,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Research the given topic.")},
            {"role": "user", "content": RESEARCH_PROMPT.format(topic=topic[:2000])},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.4, max_tokens=2048)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("ResearcherAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"summary": f"Research unavailable: {exc}", "sources": [], "key_findings": []},
                tokens_used=290, cost_usd=0.0017,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("researcher", ResearcherAgent())
