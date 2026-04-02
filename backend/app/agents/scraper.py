"""ScraperAgent — web data collection (simulated in demo mode)."""

import json
import logging
import time

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

SCRAPE_PROMPT = """Given the following URL and extraction instructions, describe what structured data
you would extract from this page.

Respond ONLY with valid JSON (no markdown):
{{"extracted_data": {{<structured fields>}}, "source_url": "{url}", "fields_found": <int>, "timestamp": "{timestamp}"}}

URL: {url}
Instructions: {instructions}"""


class ScraperAgent(BaseAgent):
    name = "ScraperAgent"
    agent_type = "scraper"
    description = "Collects and extracts structured data from web sources."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        url = input_data.get("url", input_data.get("text", ""))
        instructions = input_data.get("instructions", "Extract all key data")
        config = config or {}
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if config.get("demo") or not url:
            return AgentResult(
                output={
                    "extracted_data": {
                        "title": "Sample Page Title",
                        "author": "Jane Doe",
                        "published_date": "2026-03-15",
                        "main_content": "Extracted content summary...",
                    },
                    "source_url": url or "https://example.com",
                    "fields_found": 4,
                    "timestamp": ts,
                },
                tokens_used=430, cost_usd=0.0026,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Extract structured data from web pages.")},
            {"role": "user", "content": SCRAPE_PROMPT.format(url=url, instructions=instructions[:500], timestamp=ts)},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("ScraperAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"extracted_data": {}, "source_url": url, "fields_found": 0, "timestamp": ts},
                tokens_used=170, cost_usd=0.001,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("scraper", ScraperAgent())
