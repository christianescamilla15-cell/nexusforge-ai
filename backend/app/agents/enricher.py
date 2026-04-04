"""EnricherAgent — enriches entities with real web data + LLM synthesis."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

ENRICH_PROMPT = """Given the following extracted entities, their source text, and additional web context,
enrich each entity with verified information.

Respond ONLY with valid JSON (no markdown):
{{"enriched_entities": [{{"type": "<type>", "value": "<value>", "context": "<original context>", "enrichment": "<additional info from web/knowledge>", "related": ["<related entity>"], "verified": <true|false>}}]}}

Entities:
{entities}

Source text:
{text}

Web context (if available):
{web_context}"""


async def _web_enrich_entity(entity_value: str, entity_type: str) -> str:
    """Try to enrich an entity via web search. Returns context string or empty."""
    if entity_type not in ("organization", "person", "location"):
        return ""
    try:
        from crawl4ai import AsyncWebCrawler
        search_url = f"https://html.duckduckgo.com/html/?q={entity_value.replace(' ', '+')}"
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=search_url)
            if result.markdown:
                return result.markdown[:1000]
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("Web enrichment failed for '%s': %s", entity_value, exc)
    return ""


class EnricherAgent(BaseAgent):
    name = "EnricherAgent"
    agent_type = "enricher"
    description = "Enriches entities with real web data and cross-references."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        entities = input_data.get("entities", [])
        text = input_data.get("text", "")
        config = config or {}

        if config.get("demo") or not entities:
            return AgentResult(
                output={"enriched_entities": [
                    {"type": "person", "value": "Demo", "context": "N/A",
                     "enrichment": "Demo enrichment", "related": [], "verified": False},
                ]},
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        # Step 1: Try web enrichment for key entities (organizations, people)
        web_context_parts = []
        for ent in entities[:3]:  # limit to top 3 to avoid slow-down
            ctx = await _web_enrich_entity(ent.get("value", ""), ent.get("type", ""))
            if ctx:
                web_context_parts.append(f"{ent['value']}: {ctx[:500]}")

        web_context = "\n---\n".join(web_context_parts) if web_context_parts else "No web data available."

        # Step 2: LLM enrichment with web context
        messages = [
            {"role": "system", "content": self._build_system_prompt(
                "Enrich entities with verified information from web and knowledge."
            )},
            {"role": "user", "content": ENRICH_PROMPT.format(
                entities=json.dumps(entities, indent=2)[:2000],
                text=text[:1500],
                web_context=web_context[:1500],
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.3, max_tokens=1024)
            parsed = json.loads(resp.text)
            parsed["_enrichment_method"] = "web+llm" if web_context_parts else "llm_only"
            parsed["_web_sources_found"] = len(web_context_parts)
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
                {**e, "enrichment": "LLM unavailable", "related": [], "verified": False}
                for e in entities
            ]
            return AgentResult(
                output={"enriched_entities": enriched, "_enrichment_method": "fallback"},
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )


register_agent("enricher", EnricherAgent())
