"""TranslatorAgent — translation with quality scoring + optional back-translation."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

TRANSLATE_PROMPT = """Translate the following text to {target_lang}.
Auto-detect the source language. Preserve formatting (bullet points, headers, etc.).

Respond ONLY with valid JSON (no markdown):
{{
  "translated_text": "<translation>",
  "source_lang": "<detected language>",
  "target_lang": "{target_lang}",
  "quality_score": <0.0-1.0>,
  "quality_notes": "<any concerns about translation quality>",
  "preserved_formatting": <true|false>,
  "word_count_source": <int>,
  "word_count_target": <int>
}}

Text:
{text}"""


def _detect_source_language(text: str) -> str:
    """Simple heuristic source language detection."""
    spanish_indicators = {"el", "la", "de", "en", "que", "los", "las", "del", "por", "con", "para", "una", "es", "como", "más"}
    words = set(text.lower().split()[:50])
    es_count = len(words & spanish_indicators)
    if es_count >= 4:
        return "Spanish"
    return "English"


class TranslatorAgent(BaseAgent):
    name = "TranslatorAgent"
    agent_type = "translator"
    description = "Translates text with quality scoring, language detection, and format preservation."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = input_data.get("text", "")
        target_lang = input_data.get("target_lang", "English")
        verify = input_data.get("verify", False)
        config = config or {}

        if config.get("demo") or not text:
            return AgentResult(
                output={
                    "translated_text": "This is a demo translation.",
                    "source_lang": "Spanish",
                    "target_lang": target_lang,
                    "quality_score": 0.95,
                    "quality_notes": "Demo mode",
                    "preserved_formatting": True,
                    "word_count_source": 5,
                    "word_count_target": 6,
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        total_tokens = 0
        total_cost = 0.0

        # Auto-detect if source and target are the same
        detected_lang = _detect_source_language(text)
        if detected_lang.lower() == target_lang.lower():
            return AgentResult(
                output={
                    "translated_text": text,
                    "source_lang": detected_lang,
                    "target_lang": target_lang,
                    "quality_score": 1.0,
                    "quality_notes": "Source and target language are the same — no translation needed",
                    "preserved_formatting": True,
                    "word_count_source": len(text.split()),
                    "word_count_target": len(text.split()),
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="passthrough",
            )

        # Step 1: Translate
        messages = [
            {"role": "system", "content": self._build_system_prompt("Translate text accurately with quality assessment.")},
            {"role": "user", "content": TRANSLATE_PROMPT.format(target_lang=target_lang, text=text[:3000])},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.2, max_tokens=2048)
            parsed = clean_llm_json(resp.text)
            total_tokens += resp.tokens_input + resp.tokens_output
            total_cost += getattr(resp, "cost_usd", 0.0)

            # Step 2: Optional back-translation verification
            if verify and parsed.get("translated_text"):
                try:
                    source_lang = parsed.get("source_lang", detected_lang)
                    back_messages = [
                        {"role": "system", "content": "Translate back to the original language for verification."},
                        {"role": "user", "content": f"Translate this text to {source_lang}:\n{parsed['translated_text'][:1500]}"},
                    ]
                    back_resp = await self._resilient_llm_call(back_messages, temperature=0.1, max_tokens=1024)
                    total_tokens += back_resp.tokens_input + back_resp.tokens_output
                    total_cost += getattr(back_resp, "cost_usd", 0.0)
                    parsed["_back_translation"] = back_resp.text[:1000]
                    parsed["_verified"] = True
                except Exception:
                    parsed["_verified"] = False

            return AgentResult(
                output=parsed,
                tokens_used=total_tokens,
                cost_usd=total_cost,
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("TranslatorAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "translated_text": "",
                    "source_lang": detected_lang,
                    "target_lang": target_lang,
                    "quality_score": 0.0,
                    "quality_notes": f"Translation failed: {exc}",
                    "preserved_formatting": False,
                    "word_count_source": len(text.split()),
                    "word_count_target": 0,
                },
                tokens_used=total_tokens, cost_usd=total_cost,
                provider="local", model="fallback",
            )


register_agent("translator", TranslatorAgent())
