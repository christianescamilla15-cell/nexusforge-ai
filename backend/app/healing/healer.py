"""SelfHealer — core self-healing engine that orchestrates error recovery."""

import logging
from dataclasses import dataclass, field

from app.healing.detector import FailureDetector, ErrorClassification
from app.healing.strategies import get_strategy, HealingResult, STRATEGY_REGISTRY

logger = logging.getLogger(__name__)


@dataclass
class HealingAttemptLog:
    """Record of a healing attempt for future learning."""
    step_name: str
    error_type: str
    strategy_used: str
    success: bool
    message: str


# In-memory healing log (could be persisted to DB in production)
_healing_log: list[HealingAttemptLog] = []

# Strategy priority per error type
_STRATEGY_ORDER: dict[str, list[str]] = {
    "network": ["retry", "fallback", "skip", "escalate"],
    "timeout": ["retry", "fallback", "skip", "escalate"],
    "data_quality": ["skip", "repair", "fallback", "escalate"],
    "schema_mismatch": ["repair", "retry", "skip", "escalate"],
    "llm_error": ["retry", "repair", "fallback", "escalate"],
    "unknown": ["repair", "retry", "skip", "escalate"],
}


class SelfHealer:
    """Orchestrates error detection, classification, and recovery."""

    def __init__(self):
        self.detector = FailureDetector()

    async def attempt_heal(
        self,
        failed_step: dict,
        error_info: dict,
        execution_context: dict = None,
    ) -> HealingResult:
        """
        Attempt to heal a failed step:
        1. Classify the error using FailureDetector
        2. If recoverable, try strategies in priority order
        3. If not recoverable, log to dead letter queue and return failure
        4. Log healing attempt for future learning
        """
        execution_context = execution_context or {}
        error_message = error_info.get("error_message", str(error_info.get("error", "Unknown")))
        step_name = failed_step.get("step_name", "unknown")

        # Step 1: Classify the error
        classification = self.detector.classify(error_message, failed_step)

        logger.info(
            "SelfHealer: step '%s' error classified as %s (severity=%s, recoverable=%s)",
            step_name, classification.error_type, classification.severity, classification.is_recoverable,
        )

        # Step 2: If not recoverable, escalate immediately
        if not classification.is_recoverable:
            escalate = get_strategy("escalate")
            result = await escalate.apply(failed_step, {
                "error_type": classification.error_type,
                "severity": classification.severity,
                "error_message": error_message,
            }, execution_context)

            self._log_attempt(step_name, classification.error_type, "escalate", False, result.message)
            return result

        # Step 3: Try strategies in priority order for this error type
        strategy_order = _STRATEGY_ORDER.get(classification.error_type, ["retry", "escalate"])

        for strategy_name in strategy_order:
            if strategy_name not in STRATEGY_REGISTRY:
                continue

            strategy = get_strategy(strategy_name)
            error_ctx = {
                "error_type": classification.error_type,
                "severity": classification.severity,
                "error_message": error_message,
                "is_recoverable": classification.is_recoverable,
            }

            try:
                result = await strategy.apply(failed_step, error_ctx, execution_context)

                self._log_attempt(
                    step_name, classification.error_type, strategy_name,
                    result.success, result.message,
                )

                if result.success:
                    logger.info(
                        "SelfHealer: step '%s' healed via '%s': %s",
                        step_name, strategy_name, result.message,
                    )
                    return result

                logger.info(
                    "SelfHealer: strategy '%s' failed for step '%s': %s",
                    strategy_name, step_name, result.message,
                )

            except Exception as exc:
                logger.warning(
                    "SelfHealer: strategy '%s' raised exception for step '%s': %s",
                    strategy_name, step_name, exc,
                )
                self._log_attempt(step_name, classification.error_type, strategy_name, False, str(exc))

        # All strategies exhausted
        return HealingResult(
            success=False,
            strategy_used="none",
            output=None,
            message=f"All healing strategies exhausted for step '{step_name}' ({classification.error_type})",
        )

    def _log_attempt(self, step_name: str, error_type: str, strategy: str, success: bool, message: str):
        """Log healing attempt for future analysis."""
        _healing_log.append(HealingAttemptLog(
            step_name=step_name,
            error_type=error_type,
            strategy_used=strategy,
            success=success,
            message=message,
        ))

    @staticmethod
    def get_healing_log() -> list[dict]:
        """Return the healing attempt log as a list of dicts."""
        return [
            {
                "step_name": entry.step_name,
                "error_type": entry.error_type,
                "strategy_used": entry.strategy_used,
                "success": entry.success,
                "message": entry.message,
            }
            for entry in _healing_log
        ]
