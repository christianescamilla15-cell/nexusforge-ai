"""AnalyzerAgent — deterministic statistics first + LLM narrative insights."""

import json
import logging
import re
import math

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

ANALYZE_PROMPT = """Analyze the following text and its pre-computed statistics.
Provide sentiment analysis, topic extraction, and narrative insights.

Pre-computed statistics:
{stats}

Respond ONLY with valid JSON (no markdown):
{{
  "sentiment": "<positive|negative|neutral|mixed>",
  "topics": ["<topic1>", "<topic2>"],
  "complexity": "<simple|moderate|complex>",
  "insights": ["<insight1>", "<insight2>"],
  "statistics": {stats_json}
}}

Text:
{text}"""


def _compute_text_stats(text: str) -> dict:
    """Deterministic text statistics — instant, $0, no LLM."""
    words = text.split()
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    word_count = len(words)
    sentence_count = max(len(sentences), 1)
    avg_sentence_length = round(word_count / sentence_count, 1)

    # Vocabulary richness (type-token ratio)
    unique_words = len(set(w.lower() for w in words))
    vocab_richness = round(unique_words / max(word_count, 1), 3)

    # Readability estimate (simplified Flesch-Kincaid approximation)
    syllable_count = sum(max(1, len(re.findall(r'[aeiouy]+', w.lower()))) for w in words)
    avg_syllables = syllable_count / max(word_count, 1)
    fk_grade = round(0.39 * avg_sentence_length + 11.8 * avg_syllables - 15.59, 1)

    # Complexity classification
    if fk_grade <= 8:
        complexity = "simple"
    elif fk_grade <= 14:
        complexity = "moderate"
    else:
        complexity = "complex"

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": len(paragraphs),
        "avg_sentence_length": avg_sentence_length,
        "unique_words": unique_words,
        "vocabulary_richness": vocab_richness,
        "estimated_reading_time_sec": round(word_count / 4.2),  # ~250 wpm
        "flesch_kincaid_grade": fk_grade,
        "complexity": complexity,
    }


def _compute_numeric_stats(data: list[dict]) -> dict | None:
    """Compute stats for numeric data arrays. Returns None if not applicable."""
    if not data or not isinstance(data, list) or not isinstance(data[0], dict):
        return None

    numeric_fields = {}
    for record in data:
        for key, val in record.items():
            if isinstance(val, (int, float)):
                numeric_fields.setdefault(key, []).append(val)

    if not numeric_fields:
        return None

    stats = {}
    for field, values in numeric_fields.items():
        n = len(values)
        mean = sum(values) / n
        sorted_vals = sorted(values)
        median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        variance = sum((x - mean) ** 2 for x in values) / max(n - 1, 1)
        std_dev = math.sqrt(variance)

        # Simple anomaly detection: values > 2 std devs from mean
        anomalies = [v for v in values if abs(v - mean) > 2 * std_dev] if std_dev > 0 else []

        stats[field] = {
            "count": n,
            "mean": round(mean, 2),
            "median": round(median, 2),
            "min": min(values),
            "max": max(values),
            "std_dev": round(std_dev, 2),
            "anomalies_count": len(anomalies),
        }

    return stats


class AnalyzerAgent(BaseAgent):
    name = "AnalyzerAgent"
    agent_type = "analyzer"
    description = "Deterministic statistics + LLM-powered sentiment, topic, and insight analysis."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = input_data.get("text", "")
        data = input_data.get("data", None)
        config = config or {}

        if config.get("demo") or (not text and not data):
            return AgentResult(
                output={
                    "sentiment": "neutral",
                    "topics": ["demo"],
                    "complexity": "simple",
                    "insights": [],
                    "statistics": {"word_count": 0, "sentence_count": 0, "avg_sentence_length": 0.0},
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        # Layer 1: Deterministic statistics (instant, $0)
        text_stats = _compute_text_stats(text) if text else {}
        numeric_stats = _compute_numeric_stats(data) if data else None

        combined_stats = {**text_stats}
        if numeric_stats:
            combined_stats["numeric_analysis"] = numeric_stats

        # If text is very short, skip LLM
        if text and len(text.split()) < 10:
            return AgentResult(
                output={
                    "sentiment": "neutral",
                    "topics": [],
                    "complexity": text_stats.get("complexity", "simple"),
                    "insights": ["Text too short for detailed analysis"],
                    "statistics": combined_stats,
                    "_analysis_method": "deterministic_only",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="deterministic-stats",
            )

        # Layer 2: LLM for sentiment, topics, insights
        stats_text = "\n".join(f"- {k}: {v}" for k, v in combined_stats.items() if k != "numeric_analysis")
        if numeric_stats:
            for field, fs in numeric_stats.items():
                stats_text += f"\n- {field}: mean={fs['mean']}, median={fs['median']}, anomalies={fs['anomalies_count']}"

        messages = [
            {"role": "system", "content": self._build_system_prompt("Analyze text with statistical context.")},
            {"role": "user", "content": ANALYZE_PROMPT.format(
                stats=stats_text,
                stats_json=json.dumps(combined_stats),
                text=text[:3000] if text else json.dumps(data, default=str)[:3000],
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.2, max_tokens=512)
            parsed = json.loads(resp.text)
            # Ensure our deterministic stats are authoritative
            parsed["statistics"] = combined_stats
            parsed["_analysis_method"] = "deterministic+llm"
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("AnalyzerAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "sentiment": "unknown",
                    "topics": [],
                    "complexity": text_stats.get("complexity", "unknown"),
                    "insights": [],
                    "statistics": combined_stats,
                    "_analysis_method": "deterministic_fallback",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="deterministic-stats",
            )


register_agent("analyzer", AnalyzerAgent())
