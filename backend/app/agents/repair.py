"""RepairAgent — self-healing with error fingerprinting + degradation levels."""

import hashlib
import json
import logging
import re

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

# In-memory fingerprint cache: fingerprint -> {fix_type, success_count, fail_count}
_FINGERPRINT_CACHE: dict[str, dict] = {}

REPAIR_PROMPT = """A workflow step has failed. Analyze the error and suggest a fix.

Step name: {step_name}
Step type: {step_type}
Error message: {error}
Step config: {config}
Previous healing attempts for similar errors: {history}

Respond ONLY with valid JSON (no markdown):
{{
  "diagnosis": "<root cause analysis>",
  "fix_type": "<retry|reconfigure|skip|escalate|degrade>",
  "suggested_config": {{}},
  "can_auto_fix": <true|false>,
  "degradation_level": "<full|reduced|cached|template|honest_failure>"
}}"""

# Degradation levels — what to do when normal execution fails
DEGRADATION_LEVELS = {
    "full": "Normal execution with all capabilities",
    "reduced": "Skip non-critical enrichment steps (sentiment, summarize)",
    "cached": "Use last successful output for this step",
    "template": "Return hardcoded safe defaults",
    "honest_failure": "Return {status: 'degraded', reason: '...'} transparently",
}


def _compute_fingerprint(step_type: str, error: str) -> str:
    """Hash error pattern for fingerprint cache lookup."""
    # Normalize: strip numbers, paths, IDs to group similar errors
    normalized = re.sub(r'\b\d+\b', 'N', str(error))
    normalized = re.sub(r'[a-f0-9]{8,}', 'ID', normalized)
    normalized = re.sub(r'/[^\s]+', '/PATH', normalized)
    key = f"{step_type}:{normalized[:200]}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _get_cached_fix(fingerprint: str) -> dict | None:
    """Check if we've seen this error pattern before and have a known fix."""
    cached = _FINGERPRINT_CACHE.get(fingerprint)
    if not cached:
        return None
    if cached.get("success_count", 0) >= 2 and cached.get("success_count", 0) > cached.get("fail_count", 0):
        return cached
    return None


def _record_healing_result(fingerprint: str, fix_type: str, success: bool):
    """Record whether a healing fix worked for this fingerprint."""
    if fingerprint not in _FINGERPRINT_CACHE:
        _FINGERPRINT_CACHE[fingerprint] = {"fix_type": fix_type, "success_count": 0, "fail_count": 0}
    if success:
        _FINGERPRINT_CACHE[fingerprint]["success_count"] += 1
    else:
        _FINGERPRINT_CACHE[fingerprint]["fail_count"] += 1
    _FINGERPRINT_CACHE[fingerprint]["fix_type"] = fix_type


# Heuristic repair rules (instant, $0, no LLM)
_HEURISTIC_RULES = [
    (r"(?i)timeout|timed?\s*out",    "retry",     "Request timed out — will retry with increased timeout",   True,  "full"),
    (r"(?i)rate.?limit|429|throttle", "retry",     "Rate limit hit — will retry after backoff",               True,  "full"),
    (r"(?i)auth|401|403|forbidden",   "escalate",  "Authentication failure — requires credential fix",         False, "honest_failure"),
    (r"(?i)empty|no data|404",        "skip",      "No data available — skipping non-critical step",          True,  "reduced"),
    (r"(?i)parse|json|decode|schema", "retry",     "Malformed response — will retry with stricter prompt",    True,  "full"),
    (r"(?i)memory|oom|resource",      "degrade",   "Resource exhaustion — reducing to cached/template mode",  True,  "template"),
    (r"(?i)500|502|503|overloaded",   "retry",     "Server error — will retry with fallback provider",        True,  "full"),
]


class RepairAgent(BaseAgent):
    name = "RepairAgent"
    agent_type = "repair"
    description = "Self-healing agent with error fingerprinting, heuristic rules, and graceful degradation."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        error = input_data.get("error", "Unknown error")
        step_name = input_data.get("step_name", "unknown")
        step_type = input_data.get("step_type", "unknown")
        step_config = input_data.get("step_config", {})
        config = config or {}

        if config.get("demo"):
            return AgentResult(
                output={
                    "diagnosis": "Demo mode — no real error",
                    "fix_type": "retry",
                    "suggested_config": {},
                    "can_auto_fix": True,
                    "degradation_level": "full",
                    "_repair_method": "demo",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        error_str = str(error)

        # Layer 1: Fingerprint cache lookup (instant, $0)
        fingerprint = _compute_fingerprint(step_type, error_str)
        cached_fix = _get_cached_fix(fingerprint)
        if cached_fix:
            logger.info("RepairAgent: fingerprint cache hit for '%s' → %s", fingerprint, cached_fix["fix_type"])
            return AgentResult(
                output={
                    "diagnosis": f"Known error pattern (seen {cached_fix['success_count']}x before)",
                    "fix_type": cached_fix["fix_type"],
                    "suggested_config": step_config,
                    "can_auto_fix": True,
                    "degradation_level": "full",
                    "_repair_method": "fingerprint_cache",
                    "_fingerprint": fingerprint,
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fingerprint-cache",
            )

        # Layer 2: Heuristic rules (instant, $0)
        for pattern, fix_type, diagnosis, can_auto, deg_level in _HEURISTIC_RULES:
            if re.search(pattern, error_str):
                _record_healing_result(fingerprint, fix_type, True)
                return AgentResult(
                    output={
                        "diagnosis": diagnosis,
                        "fix_type": fix_type,
                        "suggested_config": step_config,
                        "can_auto_fix": can_auto,
                        "degradation_level": deg_level,
                        "_repair_method": "heuristic",
                        "_fingerprint": fingerprint,
                    },
                    tokens_used=0, cost_usd=0.0,
                    provider="local", model="heuristic-rules",
                )

        # Layer 3: LLM diagnosis (only for unknown error patterns)
        history_text = json.dumps(
            {k: v for k, v in _FINGERPRINT_CACHE.items() if v.get("success_count", 0) > 0},
            indent=2
        )[:500] if _FINGERPRINT_CACHE else "No previous healing history."

        messages = [
            {"role": "system", "content": self._build_system_prompt(
                "Diagnose and fix the failed step. Consider degradation as an option."
            )},
            {"role": "user", "content": REPAIR_PROMPT.format(
                step_name=step_name,
                step_type=step_type,
                error=error_str[:500],
                config=json.dumps(step_config, default=str)[:500],
                history=history_text,
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.2, max_tokens=512)
            parsed = clean_llm_json(resp.text)
            parsed["_repair_method"] = "llm"
            parsed["_fingerprint"] = fingerprint
            # Record for future fingerprint cache
            _record_healing_result(fingerprint, parsed.get("fix_type", "retry"), True)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("RepairAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "diagnosis": f"Unknown error, LLM unavailable: {error_str[:200]}",
                    "fix_type": "retry",
                    "suggested_config": step_config,
                    "can_auto_fix": True,
                    "degradation_level": "reduced",
                    "_repair_method": "heuristic_fallback",
                    "_fingerprint": fingerprint,
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )


register_agent("repair", RepairAgent())
