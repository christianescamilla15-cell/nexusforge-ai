"""ComplianceAgent — deterministic PII detection + LLM regulatory analysis."""

import json
import logging
import re

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

# PII regex patterns (deterministic, instant, $0)
_PII_PATTERNS = [
    ("credit_card", r'\b(?:\d{4}[-\s]?){3}\d{4}\b', "PCI-DSS 3.4"),
    ("ssn", r'\b\d{3}-\d{2}-\d{4}\b', "Privacy"),
    ("email", r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "GDPR Art.9"),
    ("phone_mx", r'\b(?:\+?52\s?)?(?:\d{2,3}\s?)?\d{4}[\s-]?\d{4}\b', "LFPDPPP"),
    ("phone_us", r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', "Privacy"),
    ("curp", r'\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b', "LFPDPPP"),
    ("rfc", r'\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b', "SAT/Fiscal"),
    ("iban", r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b', "PCI-DSS"),
    ("ip_address", r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', "Privacy"),
    ("passport", r'\b[A-Z]{1,2}\d{6,9}\b', "Privacy"),
]

COMPLIANCE_PROMPT = """Analyze this text for regulatory compliance issues.
PII scan has already been done (results below). Focus on regulatory/legal analysis.

Frameworks to check: GDPR, HIPAA, PCI-DSS, SOX, LFPDPPP (Mexico), NOM-151
PII findings: {pii_findings}

Respond ONLY with valid JSON (no markdown):
{{
  "is_compliant": <true|false>,
  "issues": [{{"rule": "<regulation>", "violation": "<description>", "severity": "<high|medium|low>", "evidence": "<quote from text>"}}],
  "risk_score": <0-100>,
  "pii_detected": {pii_json},
  "recommendations": ["<action>"]
}}

Text:
{text}"""


def _scan_pii(text: str) -> list[dict]:
    """Deterministic PII scanning with regex patterns. Instant, $0."""
    findings = []
    for pii_type, pattern, regulation in _PII_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            # Mask the actual values for safety
            masked = [m[:4] + "***" if len(m) > 4 else "***" for m in matches[:5]]
            findings.append({
                "type": pii_type,
                "count": len(matches),
                "regulation": regulation,
                "severity": "high" if pii_type in ("credit_card", "ssn", "curp") else "medium",
                "masked_samples": masked[:3],
            })
    return findings


def _luhn_check(card_number: str) -> bool:
    """Luhn algorithm to verify credit card numbers."""
    digits = [int(d) for d in card_number.replace("-", "").replace(" ", "") if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class ComplianceAgent(BaseAgent):
    name = "ComplianceAgent"
    agent_type = "compliance"
    description = "Deterministic PII detection (regex) + LLM regulatory compliance analysis."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        text = self._extract_text(input_data)
        config = config or {}

        if config.get("demo") or not text:
            return AgentResult(
                output={
                    "is_compliant": False,
                    "issues": [
                        {"rule": "GDPR Art.13", "violation": "Missing data processing disclosure", "severity": "high", "evidence": "N/A"},
                        {"rule": "PCI-DSS 3.4", "violation": "Potential unmasked card numbers", "severity": "medium", "evidence": "N/A"},
                    ],
                    "risk_score": 65,
                    "pii_detected": [],
                    "recommendations": ["Add privacy disclosure", "Mask card numbers"],
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        # Layer 1: Deterministic PII scan (instant, $0)
        pii_findings = _scan_pii(text)

        # Verify credit card numbers with Luhn
        for finding in pii_findings:
            if finding["type"] == "credit_card":
                cc_matches = re.findall(r'(?:\d{4}[-\s]?){3}\d{4}', text)
                valid_count = sum(1 for cc in cc_matches if _luhn_check(cc))
                finding["luhn_valid"] = valid_count
                if valid_count > 0:
                    finding["severity"] = "critical"

        # Calculate risk from PII alone
        pii_risk = min(100, sum(
            30 if f["severity"] == "critical" else (20 if f["severity"] == "high" else 10)
            for f in pii_findings
        ))

        # If high PII risk, add immediate issues without LLM
        pii_issues = []
        for f in pii_findings:
            if f["severity"] in ("high", "critical"):
                pii_issues.append({
                    "rule": f["regulation"],
                    "violation": f"Detected {f['count']} {f['type']} instance(s)",
                    "severity": f["severity"],
                    "evidence": f"Masked: {f['masked_samples']}",
                })

        # Layer 2: LLM regulatory analysis
        pii_text = json.dumps(pii_findings, indent=2) if pii_findings else "No PII detected"
        messages = [
            {"role": "system", "content": self._build_system_prompt_v2(
                "Analyze for regulatory compliance. Focus on GDPR, HIPAA, PCI-DSS, LFPDPPP."
            )},
            {"role": "user", "content": COMPLIANCE_PROMPT.format(
                pii_findings=pii_text,
                pii_json=json.dumps(pii_findings),
                text=text[:3000],
            )},
        ]

        try:
            # Phase 3 Feature 3 — Memory Tool opt-in path.
            # When NEXUSFORGE_MEMORY_TOOL_COMPLIANCE=1 is set AND the
            # Anthropic API key is configured, route the LLM call
            # through a multi-turn agent loop with the memory_20250818
            # tool enabled. The agent can then accumulate learned
            # false-positive patterns and tenant-specific policy
            # deltas across runs (see docs/anthropic-features-
            # research.md §5). OFF BY DEFAULT — production behavior
            # is byte-identical to pre-Phase-3.
            import os as _os
            if _os.environ.get("NEXUSFORGE_MEMORY_TOOL_COMPLIANCE", "0") == "1":
                from app.llm.agent_loop import run_memory_loop_for_agent
                from app.llm.provider import LLMResponse as _LLMResponse
                from app.config import settings as _settings

                api_key = getattr(_settings, "anthropic_api_key", "") or ""
                if not api_key:
                    # No key -> fall back to the legacy router path.
                    resp = await self._resilient_llm_call(
                        messages, temperature=0.1, max_tokens=1024
                    )
                else:
                    # Extract system + non-system messages for the loop.
                    system_content = ""
                    loop_messages: list[dict] = []
                    for _m in messages:
                        if _m.get("role") == "system":
                            system_content = _m.get("content", "")
                        else:
                            loop_messages.append(_m)

                    loop_resp = await run_memory_loop_for_agent(
                        agent_id="ComplianceAgent",
                        system=system_content,
                        messages=loop_messages,
                        api_key=api_key,
                        max_tokens=1024,
                        temperature=0.1,
                        max_turns=5,
                    )
                    # Adapt AgentLoopResponse to the LLMResponse shape
                    # so the rest of this method stays unchanged.
                    resp = _LLMResponse(
                        text=loop_resp.text,
                        tokens_input=loop_resp.tokens_input,
                        tokens_output=loop_resp.tokens_output,
                        model=loop_resp.model,
                        provider=loop_resp.provider,
                        cost_usd=loop_resp.cost_usd,
                        thinking=loop_resp.thinking,
                    )
            else:
                # Legacy path — unchanged.
                resp = await self._resilient_llm_call(
                    messages, temperature=0.1, max_tokens=1024
                )

            parsed = clean_llm_json(resp.text)
            # Merge PII findings as authoritative
            parsed["pii_detected"] = pii_findings
            parsed["risk_score"] = max(parsed.get("risk_score", 0), pii_risk)
            parsed["is_compliant"] = parsed["risk_score"] < 30 and not pii_issues
            # Prepend PII issues
            parsed["issues"] = pii_issues + parsed.get("issues", [])
            parsed["_compliance_method"] = "pii_regex+llm"
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("ComplianceAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "is_compliant": pii_risk == 0,
                    "issues": pii_issues,
                    "risk_score": pii_risk,
                    "pii_detected": pii_findings,
                    "recommendations": ["Manual review needed (LLM unavailable)"] if pii_findings else [],
                    "_compliance_method": "pii_regex_only",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="pii-regex",
            )


register_agent("compliance", ComplianceAgent())
