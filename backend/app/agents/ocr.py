"""OCRAgent — document text extraction with PyPDF2 for real PDFs + LLM for descriptions."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

OCR_PROMPT = """You are given raw text extracted from a document.
Clean it up, fix encoding issues, and structure the output.

Respond ONLY with valid JSON (no markdown):
{{
  "extracted_text": "<cleaned structured text>",
  "confidence": <0.0-1.0>,
  "page_count": <int>,
  "language_detected": "<language>",
  "document_type": "<invoice|contract|letter|report|form|other>",
  "key_fields": {{"<field_name>": "<value>"}}
}}

Raw extracted text:
{text}"""

DESCRIBE_OCR_PROMPT = """Based on the description of a document image, generate realistic extracted text.

Respond ONLY with valid JSON (no markdown):
{{"extracted_text": "<full extracted text>", "confidence": <0.0-1.0>, "page_count": <int>, "language_detected": "<language>", "document_type": "<type>", "key_fields": {{}}}}

Document description:
{description}"""


def _extract_pdf_text(file_path: str) -> tuple[str, int]:
    """Extract text from PDF using PyPDF2 (already in requirements.txt). Returns (text, page_count)."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n--- Page Break ---\n\n".join(pages), len(reader.pages)
    except ImportError:
        logger.info("PyPDF2 not available for PDF extraction")
        return "", 0
    except Exception as exc:
        logger.warning("PDF extraction failed: %s", exc)
        return "", 0


def _detect_language(text: str) -> str:
    """Simple heuristic language detection."""
    spanish_words = {"el", "la", "de", "en", "que", "los", "las", "del", "por", "con", "para", "una", "como"}
    words = set(text.lower().split()[:100])
    es_count = len(words & spanish_words)
    return "Spanish" if es_count >= 3 else "English"


def _detect_document_type(text: str) -> str:
    """Heuristic document type detection."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["invoice", "factura", "total", "subtotal", "bill to"]):
        return "invoice"
    if any(w in text_lower for w in ["contract", "contrato", "agreement", "hereby", "parties"]):
        return "contract"
    if any(w in text_lower for w in ["dear", "sincerely", "estimado", "atentamente"]):
        return "letter"
    if any(w in text_lower for w in ["report", "reporte", "findings", "conclusion", "summary"]):
        return "report"
    return "other"


class OCRAgent(BaseAgent):
    name = "OCRAgent"
    agent_type = "ocr"
    description = "Extracts text from PDFs (real) and document descriptions (LLM-assisted)."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        description = input_data.get("description", input_data.get("text", ""))
        file_path = input_data.get("file_path", "")
        config = config or {}

        if config.get("demo") or (not description and not file_path):
            return AgentResult(
                output={
                    "extracted_text": "INVOICE #2026-0342\nDate: March 15, 2026\nBill To: Acme Corp\nTotal: $4,250.00",
                    "confidence": 0.94,
                    "page_count": 1,
                    "language_detected": "English",
                    "document_type": "invoice",
                    "key_fields": {"invoice_number": "2026-0342", "date": "2026-03-15", "total": "$4,250.00"},
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        # Layer 1: Real PDF extraction (if file_path provided)
        if file_path and file_path.lower().endswith(".pdf"):
            raw_text, page_count = _extract_pdf_text(file_path)
            if raw_text:
                lang = _detect_language(raw_text)
                doc_type = _detect_document_type(raw_text)

                # Use LLM to clean and structure the extracted text
                messages = [
                    {"role": "system", "content": self._build_system_prompt("Clean and structure OCR text.")},
                    {"role": "user", "content": OCR_PROMPT.format(text=raw_text[:3000])},
                ]
                try:
                    resp = await self._resilient_llm_call(messages, temperature=0.1, max_tokens=2048)
                    parsed = json.loads(resp.text)
                    parsed["page_count"] = page_count
                    parsed["_extraction_method"] = "pypdf2+llm"
                    return AgentResult(
                        output=parsed,
                        tokens_used=resp.tokens_input + resp.tokens_output,
                        cost_usd=getattr(resp, "cost_usd", 0.0),
                        provider=resp.provider, model=resp.model,
                    )
                except Exception:
                    # Return raw extraction without LLM cleanup
                    return AgentResult(
                        output={
                            "extracted_text": raw_text[:5000],
                            "confidence": 0.75,
                            "page_count": page_count,
                            "language_detected": lang,
                            "document_type": doc_type,
                            "key_fields": {},
                            "_extraction_method": "pypdf2_only",
                        },
                        tokens_used=0, cost_usd=0.0,
                        provider="local", model="pypdf2",
                    )

        # Layer 2: LLM-based OCR from description
        messages = [
            {"role": "system", "content": self._build_system_prompt("Extract text from document images.")},
            {"role": "user", "content": DESCRIBE_OCR_PROMPT.format(description=description[:2000])},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.1, max_tokens=2048)
            parsed = json.loads(resp.text)
            parsed["_extraction_method"] = "llm_from_description"
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("OCRAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "extracted_text": "", "confidence": 0.0, "page_count": 0,
                    "language_detected": "unknown", "document_type": "other", "key_fields": {},
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )


register_agent("ocr", OCRAgent())
