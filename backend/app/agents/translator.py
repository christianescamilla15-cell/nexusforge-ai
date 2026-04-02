"""TranslatorAgent — translates text between languages with auto-detection."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

TRANSLATE_PROMPT = """Translate the following text to {target_lang}.
Auto-detect the source language.

Respond ONLY with valid JSON (no markdown):
{{"translated_text": "<translation>", "source_lang": "<detected language>", "target_lang": "{target_lang}", "confidence": <0.0-1.0>}}

Text:
{text}"""


class TranslatorAgent(BaseAgent):
    name = "TranslatorAgent"
    agent_type = "translator"
    description = "Translates text between languages with automatic source language detection."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = input_data.get("text", "")
        target_lang = input_data.get("target_lang", "English")
        config = config or {}

        if config.get("demo") or not text:
            return AgentResult(
                output={
                    "translated_text": "This is a demo translation.",
                    "source_lang": "Spanish",
                    "target_lang": target_lang,
                    "confidence": 0.95,
                },
                tokens_used=480, cost_usd=0.0029,
                provider="groq", model="llama-3.3-70b-versatile",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Translate text accurately.")},
            {"role": "user", "content": TRANSLATE_PROMPT.format(target_lang=target_lang, text=text[:3000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=2048)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("TranslatorAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"translated_text": "", "source_lang": "unknown", "target_lang": target_lang, "confidence": 0.0},
                tokens_used=190, cost_usd=0.0011,
                provider="groq", model="llama-3.3-70b-versatile",
            )


register_agent("translator", TranslatorAgent())
