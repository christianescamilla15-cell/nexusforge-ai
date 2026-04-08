"""FailureDetector — classifies step execution errors for self-healing."""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ErrorClassification:
    """Result of error analysis."""
    error_type: str          # network, timeout, data_quality, schema_mismatch, llm_error, unknown
    severity: str            # low, medium, high, critical
    is_recoverable: bool
    suggested_action: str    # retry, skip, repair, escalate, fallback


# Pattern-based classification rules
_ERROR_PATTERNS = [
    # Network errors
    (r"(?i)(connection|connect|network|dns|resolve|refused|reset|socket)",
     "network", "medium", True, "retry"),
    # Timeouts
    (r"(?i)(timeout|timed?\s*out|deadline|exceeded)",
     "timeout", "medium", True, "retry"),
    # Rate limits
    (r"(?i)(rate.?limit|429|too many requests|throttle|quota)",
     "network", "low", True, "retry"),
    # Authentication
    (r"(?i)(auth|401|403|forbidden|unauthorized|credential|api.?key|token.?invalid)",
     "network", "critical", False, "escalate"),
    # Schema / validation
    (r"(?i)(schema|validation|invalid.?json|parse.?error|unexpected.?token|decode)",
     "schema_mismatch", "medium", True, "repair"),
    # Data quality
    (r"(?i)(empty|missing|null|none|no data|not found|404)",
     "data_quality", "low", True, "skip"),
    # LLM-specific
    (r"(?i)(content.?filter|safety|moderation|context.?length|max.?tokens|overloaded|500|502|503)",
     "llm_error", "medium", True, "retry"),
    # Out of memory / resource
    (r"(?i)(memory|oom|resource|capacity|disk)",
     "llm_error", "high", False, "escalate"),
]


class FailureDetector:
    """Analyzes step execution results and classifies errors."""

    def classify(self, error_message: str, step_result: dict = None) -> ErrorClassification:
        """Classify an error and recommend a recovery action."""
        step_result = step_result or {}
        error_str = str(error_message)

        for pattern, error_type, severity, recoverable, action in _ERROR_PATTERNS:
            if re.search(pattern, error_str):
                logger.info(
                    "FailureDetector: classified '%s' as %s (%s)",
                    error_str[:80], error_type, action,
                )
                return ErrorClassification(
                    error_type=error_type,
                    severity=severity,
                    is_recoverable=recoverable,
                    suggested_action=action,
                )

        # Unknown error — always attempt repair first (recoverable by default)
        # Short cryptic errors are often transient; long ones have diagnostic info
        return ErrorClassification(
            error_type="unknown",
            severity="high",
            is_recoverable=True,
            suggested_action="repair",
        )
