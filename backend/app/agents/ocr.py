"""OCRAgent — text extraction from images/scans (simulated)."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent
from app.llm.router import get_router

logger = logging.getLogger(__name__)

OCR_PROMPT = """Simulate OCR text extraction from a document image.
Based on the description below, generate realistic extracted text output.

Respond ONLY with valid JSON (no markdown):
{{"extracted_text": "<full extracted text>", "confidence": <0.0-1.0>, "page_count": <int>, "language_detected": "<language>"}}

Document description:
{description}"""


class OCRAgent(BaseAgent):
    name = "OCRAgent"
    agent_type = "ocr"
    description = "Extracts text from images and scanned documents."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        description = input_data.get("description", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not description:
            return AgentResult(
                output={
                    "extracted_text": "INVOICE #2026-0342\nDate: March 15, 2026\nBill To: Acme Corp\nTotal: $4,250.00",
                    "confidence": 0.94,
                    "page_count": 1,
                    "language_detected": "English",
                },
                provider="local", model="none",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Extract text from document images.")},
            {"role": "user", "content": OCR_PROMPT.format(description=description[:2000])},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.1, max_tokens=2048)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("OCRAgent LLM fallback: %s", exc)
            return AgentResult(
                output={"extracted_text": "", "confidence": 0.0, "page_count": 0, "language_detected": "unknown"},
                provider="local", model="fallback",
            )


register_agent("ocr", OCRAgent())
