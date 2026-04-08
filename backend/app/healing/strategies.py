"""Healing strategies — different recovery approaches for failed steps."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.agents.registry import get_agent

logger = logging.getLogger(__name__)


@dataclass
class HealingResult:
    """Result of a healing strategy attempt."""
    success: bool
    strategy_used: str
    output: dict | None
    message: str


class HealingStrategy(ABC):
    """Abstract healing strategy."""

    name: str = "unnamed"

    @abstractmethod
    async def apply(
        self,
        failed_step: dict,
        error_info: dict,
        context: dict,
    ) -> HealingResult:
        pass


class RetryStrategy(HealingStrategy):
    """Retry the same step with modified config (different LLM, lower temperature)."""

    name = "retry"

    async def apply(self, failed_step: dict, error_info: dict, context: dict) -> HealingResult:
        step_type = failed_step.get("step_type", "")
        config = dict(failed_step.get("config", {}))
        input_data = failed_step.get("input_data", {})

        # Modify config for retry
        config["temperature"] = max(0.0, config.get("temperature", 0.7) - 0.2)
        config["max_tokens"] = min(4096, config.get("max_tokens", 1024) + 512)
        config["_healing_retry"] = True

        try:
            agent = get_agent(step_type)
            result = await agent.run(input_data, config)
            return HealingResult(
                success=True,
                strategy_used=self.name,
                output=result.output,
                message=f"Retry succeeded with modified config for '{step_type}'",
            )
        except Exception as exc:
            return HealingResult(
                success=False,
                strategy_used=self.name,
                output=None,
                message=f"Retry failed: {exc}",
            )


class SkipStrategy(HealingStrategy):
    """Skip the failed step and use default/empty output."""

    name = "skip"

    async def apply(self, failed_step: dict, error_info: dict, context: dict) -> HealingResult:
        step_name = failed_step.get("step_name", "unknown")
        default_output = context.get("default_outputs", {}).get(step_name, {})

        return HealingResult(
            success=True,
            strategy_used=self.name,
            output=default_output or {"_skipped": True, "_reason": error_info.get("error_type", "unknown")},
            message=f"Skipped step '{step_name}' with default output",
        )


class RepairStrategy(HealingStrategy):
    """Invoke RepairAgent to diagnose and generate a fix."""

    name = "repair"

    async def apply(self, failed_step: dict, error_info: dict, context: dict) -> HealingResult:
        try:
            repair_agent = get_agent("repair")
            repair_input = {
                "step_name": failed_step.get("step_name", "unknown"),
                "step_type": failed_step.get("step_type", "unknown"),
                "error": error_info.get("error_message", "Unknown error"),
                "step_config": failed_step.get("config", {}),
            }
            repair_result = await repair_agent.run(repair_input, failed_step.get("config", {}))

            diagnosis = repair_result.output
            if diagnosis.get("can_auto_fix", False):
                # Try re-executing with suggested config
                suggested = diagnosis.get("suggested_config", {})
                merged_config = {**failed_step.get("config", {}), **suggested, "_healed": True}

                try:
                    agent = get_agent(failed_step.get("step_type", ""))
                    result = await agent.run(failed_step.get("input_data", {}), merged_config)
                    return HealingResult(
                        success=True,
                        strategy_used=self.name,
                        output=result.output,
                        message=f"Repair succeeded: {diagnosis.get('diagnosis', '')}",
                    )
                except Exception as exc:
                    return HealingResult(
                        success=False,
                        strategy_used=self.name,
                        output=None,
                        message=f"Repair agent suggested fix but re-execution failed: {exc}",
                    )

            return HealingResult(
                success=False,
                strategy_used=self.name,
                output=None,
                message=f"Repair agent cannot auto-fix: {diagnosis.get('diagnosis', '')}",
            )

        except Exception as exc:
            return HealingResult(
                success=False,
                strategy_used=self.name,
                output=None,
                message=f"RepairStrategy failed: {exc}",
            )


class EscalateStrategy(HealingStrategy):
    """Mark for human review and pause pipeline."""

    name = "escalate"

    async def apply(self, failed_step: dict, error_info: dict, context: dict) -> HealingResult:
        step_name = failed_step.get("step_name", "unknown")
        return HealingResult(
            success=False,
            strategy_used=self.name,
            output=None,
            message=(
                f"Step '{step_name}' requires human review. "
                f"Error type: {error_info.get('error_type', 'unknown')}, "
                f"Severity: {error_info.get('severity', 'unknown')}"
            ),
        )


class FallbackStrategy(HealingStrategy):
    """Use cached result from previous successful run or context cache."""

    name = "fallback"

    async def apply(self, failed_step: dict, error_info: dict, context: dict) -> HealingResult:
        import json as _json
        step_name = failed_step.get("step_name", "unknown")

        # 1. Check context-provided cache first
        cache = context.get("result_cache", {})
        cached_result = cache.get(step_name)
        if cached_result:
            return HealingResult(
                success=True,
                strategy_used=self.name,
                output=cached_result,
                message=f"Using cached result for step '{step_name}'",
            )

        # 2. Query DB for last successful execution of same step type
        step_type = failed_step.get("step_type", "")
        if step_type:
            try:
                from app.db.client import get_db_pool
                pool = await get_db_pool()
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """SELECT output_data FROM step_executions
                           WHERE step_name = $1 AND status = 'completed'
                             AND output_data IS NOT NULL
                           ORDER BY completed_at DESC LIMIT 1""",
                        step_name,
                    )
                if row and row["output_data"]:
                    output = _json.loads(row["output_data"]) if isinstance(row["output_data"], str) else row["output_data"]
                    return HealingResult(
                        success=True,
                        strategy_used=self.name,
                        output=output,
                        message=f"Using last successful DB result for step '{step_name}'",
                    )
            except Exception as exc:
                logger.warning("FallbackStrategy DB lookup failed: %s", exc)

        return HealingResult(
            success=False,
            strategy_used=self.name,
            output=None,
            message=f"No cached or historical result available for step '{step_name}'",
        )


# Strategy registry
STRATEGY_REGISTRY: dict[str, HealingStrategy] = {
    "retry": RetryStrategy(),
    "skip": SkipStrategy(),
    "repair": RepairStrategy(),
    "escalate": EscalateStrategy(),
    "fallback": FallbackStrategy(),
}


def get_strategy(name: str) -> HealingStrategy:
    """Get a healing strategy by name."""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown healing strategy: '{name}'. Available: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name]
