"""ScraperAgent — real web scraping via Crawl4AI + LLM extraction.

Uses Crawl4AI (Apache-2.0) for actual web fetching, then optionally
sends the extracted markdown to the LLM for structured extraction
based on user instructions.
"""

import json
import logging
import time

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are given real content scraped from a web page.
Extract structured data according to the instructions.

Respond ONLY with valid JSON (no markdown):
{{"extracted_data": {{<structured fields>}}, "source_url": "{url}", "fields_found": <int>, "timestamp": "{timestamp}"}}

Instructions: {instructions}

--- Scraped Content (first 3000 chars) ---
{content}"""


async def _crawl4ai_fetch(url: str) -> dict:
    """Fetch URL using Crawl4AI. Returns {markdown, title, success, error}."""
    try:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return {
                "markdown": result.markdown[:6000] if result.markdown else "",
                "title": getattr(result, "title", "") or "",
                "success": result.success if hasattr(result, "success") else bool(result.markdown),
                "error": None,
            }
    except ImportError:
        logger.info("crawl4ai not installed, falling back to httpx")
        return await _httpx_fetch(url)
    except Exception as exc:
        logger.warning("Crawl4AI failed for %s: %s, falling back to httpx", url, exc)
        return await _httpx_fetch(url)


async def _httpx_fetch(url: str) -> dict:
    """Simple httpx fallback for when Crawl4AI is unavailable."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "NexusForge-ScraperAgent/1.0"})
            resp.raise_for_status()
            text = resp.text[:6000]
            # Try to extract title from HTML
            title = ""
            if "<title>" in text.lower():
                start = text.lower().index("<title>") + 7
                end = text.lower().index("</title>", start) if "</title>" in text.lower()[start:] else start + 100
                title = text[start:end].strip()
            return {"markdown": text, "title": title, "success": True, "error": None}
    except Exception as exc:
        return {"markdown": "", "title": "", "success": False, "error": str(exc)}


class ScraperAgent(BaseAgent):
    name = "ScraperAgent"
    agent_type = "scraper"
    description = "Collects and extracts structured data from web sources using real web scraping."

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
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        # Step 1: Real web scraping
        fetch_result = await _crawl4ai_fetch(url)

        if not fetch_result["success"]:
            return AgentResult(
                output={
                    "extracted_data": {},
                    "source_url": url,
                    "fields_found": 0,
                    "timestamp": ts,
                    "error": fetch_result.get("error", "Failed to fetch URL"),
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="crawl4ai",
            )

        content = fetch_result["markdown"]

        # Step 2: LLM extraction from real scraped content
        messages = [
            {"role": "system", "content": self._build_system_prompt(
                "Extract structured data from scraped web content."
            )},
            {"role": "user", "content": EXTRACT_PROMPT.format(
                url=url, instructions=instructions[:500],
                timestamp=ts, content=content[:3000],
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.2, max_tokens=1024)
            parsed = clean_llm_json(resp.text)
            # Enrich with scraping metadata
            parsed["_scraping"] = {
                "method": "crawl4ai" if "crawl4ai" not in str(fetch_result.get("error", "")) else "httpx",
                "title": fetch_result["title"],
                "content_length": len(content),
            }
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("ScraperAgent LLM extraction failed: %s", exc)
            # Return raw scraped content as fallback
            return AgentResult(
                output={
                    "extracted_data": {"raw_content": content[:2000], "title": fetch_result["title"]},
                    "source_url": url,
                    "fields_found": 1,
                    "timestamp": ts,
                    "_scraping": {"method": "raw_fallback", "content_length": len(content)},
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="crawl4ai",
            )


register_agent("scraper", ScraperAgent())
