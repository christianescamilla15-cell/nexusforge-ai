"""NormalizerAgent — deterministic normalization first, LLM for ambiguous cases."""

import json
import logging
import re
from datetime import datetime

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

NORMALIZE_PROMPT = """Normalize the following raw data records into a consistent schema.
The deterministic normalizer has already handled basic formatting.
Focus on: resolving ambiguous fields, fixing semantic inconsistencies, and flagging near-duplicates.

Respond ONLY with valid JSON (no markdown):
{{"normalized_records": [{{...}}], "dedup_count": <int>, "schema_applied": "<description>", "ambiguous_fields": ["<field that needed LLM judgment>"]}}

Raw data (after basic normalization):
{data}"""

# Date format patterns — DD/MM/YYYY convention (Latin America / Europe default)
_DATE_PATTERNS = [
    # DD/MM/YYYY → YYYY-MM-DD (LatAm convention: day first)
    (r'(\d{1,2})/(\d{1,2})/(\d{4})', lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),
    # DD-MM-YYYY → YYYY-MM-DD
    (r'(\d{1,2})-(\d{1,2})-(\d{4})', lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),
    # YYYY/MM/DD → YYYY-MM-DD (ISO-like, keep as-is)
    (r'(\d{4})/(\d{1,2})/(\d{1,2})', lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"),
]


def _normalize_value(value, field_name: str = "") -> tuple:
    """Deterministic normalization. Returns (normalized_value, was_changed)."""
    if not isinstance(value, str):
        return value, False

    original = value
    v = value.strip()

    # Title Case for name-like fields
    name_fields = {"name", "nombre", "author", "autor", "company", "empresa", "city", "ciudad"}
    if field_name.lower() in name_fields:
        v = v.title()

    # ISO 8601 dates
    for pattern, replacement in _DATE_PATTERNS:
        if re.match(pattern, v):
            v = re.sub(pattern, replacement, v)
            break

    # Currency normalization: "$1,234.56" → 1234.56
    if re.match(r'^\$?\s*[\d,]+\.?\d*$', v):
        v = v.replace('$', '').replace(',', '').strip()
        try:
            v = str(round(float(v), 2))
        except ValueError:
            pass

    # Phone normalization (basic: strip non-digits, keep +)
    if field_name.lower() in {"phone", "telefono", "tel", "celular", "mobile"}:
        digits = re.sub(r'[^\d+]', '', v)
        if len(digits) >= 10:
            v = digits

    # Email lowercase
    if field_name.lower() in {"email", "correo", "mail"} or "@" in v:
        v = v.lower()

    # Unicode cleanup (basic)
    v = v.replace('\xa0', ' ').replace('\u200b', '').strip()

    return v, v != original


def _normalize_records(data) -> tuple[list, int, list[str]]:
    """Apply deterministic normalization to a list of records.
    Returns (normalized_records, changes_count, changed_fields).
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return [], 0, []

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        return [], 0, []

    changes = 0
    changed_fields = set()
    normalized = []

    for record in data:
        if not isinstance(record, dict):
            normalized.append(record)
            continue
        new_record = {}
        for key, val in record.items():
            norm_val, changed = _normalize_value(val, key)
            new_record[key] = norm_val
            if changed:
                changes += 1
                changed_fields.add(key)
        normalized.append(new_record)

    # Simple exact dedup
    seen = set()
    deduped = []
    dup_count = 0
    for rec in normalized:
        key = json.dumps(rec, sort_keys=True)
        if key not in seen:
            seen.add(key)
            deduped.append(rec)
        else:
            dup_count += 1

    return deduped, dup_count, list(changed_fields)


class NormalizerAgent(BaseAgent):
    name = "NormalizerAgent"
    agent_type = "normalizer"
    description = "Deterministic data normalization (dates, names, amounts, dedup) with LLM for ambiguous cases."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        data = input_data.get("data") or self._extract_text(input_data)
        config = config or {}

        if config.get("demo") or not data:
            return AgentResult(
                output={
                    "normalized_records": [
                        {"name": "John Doe", "date": "2026-01-15", "amount": "1500.00"},
                        {"name": "Jane Smith", "date": "2026-02-20", "amount": "2300.50"},
                    ],
                    "dedup_count": 1,
                    "schema_applied": "Demo — standard name/date/amount schema",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        # Layer 1: Deterministic normalization (instant, $0)
        normalized, dup_count, changed_fields = _normalize_records(data)

        if normalized and not changed_fields:
            # Data was already clean — no LLM needed
            return AgentResult(
                output={
                    "normalized_records": normalized,
                    "dedup_count": dup_count,
                    "schema_applied": "Data already normalized — no changes needed",
                    "_normalization_method": "deterministic_only",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="deterministic-rules",
            )

        if normalized and len(normalized) <= 20:
            # Small dataset, deterministic was enough
            return AgentResult(
                output={
                    "normalized_records": normalized,
                    "dedup_count": dup_count,
                    "schema_applied": f"Deterministic: normalized {len(changed_fields)} fields ({', '.join(changed_fields)})",
                    "_normalization_method": "deterministic",
                    "_fields_changed": changed_fields,
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="deterministic-rules",
            )

        # Layer 2: LLM for complex/ambiguous normalization
        raw = json.dumps(normalized if normalized else data, indent=2, default=str)
        messages = [
            {"role": "system", "content": self._build_system_prompt("Normalize and clean data records.")},
            {"role": "user", "content": NORMALIZE_PROMPT.format(data=raw[:3000])},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.1, max_tokens=2048)
            parsed = clean_llm_json(resp.text)
            parsed["_normalization_method"] = "deterministic+llm"
            parsed["_fields_changed"] = changed_fields
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("NormalizerAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "normalized_records": normalized,
                    "dedup_count": dup_count,
                    "schema_applied": f"Deterministic only (LLM unavailable: {exc})",
                    "_normalization_method": "deterministic_fallback",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="deterministic-rules",
            )


register_agent("normalizer", NormalizerAgent())
