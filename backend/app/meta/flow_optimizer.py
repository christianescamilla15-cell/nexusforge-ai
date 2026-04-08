"""Flow Optimizer — optimizes DAG execution using predictive memory.

Analyzes historical data to:
- Reorder steps (fail-fast: high-risk steps first)
- Identify parallelization opportunities
- Predict cost/duration before execution
- Recommend model pre-warming
"""

import logging
from typing import Any

from app.meta.schemas import DAGOptimization

logger = logging.getLogger(__name__)


class FlowOptimizer:
    """Optimizes workflow DAG execution based on historical patterns."""

    async def optimize(
        self,
        step_names: list[str],
        parallel_groups: list[list[str]],
    ) -> DAGOptimization:
        """Analyze a DAG and produce optimization recommendations."""

        try:
            from app.memory.predictive import PredictiveMemory
            from app.llm.router import _AGENT_MODEL_MAP
            predictive = PredictiveMemory()
        except Exception as e:
            logger.warning("FlowOptimizer: predictive memory unavailable: %s", e)
            return DAGOptimization(
                original_groups=parallel_groups,
                optimized_groups=parallel_groups,
            )

        # Get predictions for each step
        predictions = {}
        for step in step_names:
            try:
                pred = await predictive.predict_execution(step)
                predictions[step] = pred
            except Exception:
                predictions[step] = {"fallback_probability": 0, "error_probability": 0,
                                     "estimated_duration_sec": 0, "estimated_cost_usd": 0,
                                     "confidence": 0}

        # Build risk map
        risk_per_step = {}
        for step, pred in predictions.items():
            risk = pred.get("error_probability", 0) + pred.get("fallback_probability", 0) * 0.3
            risk_per_step[step] = round(risk, 3)

        # Optimize groups: put high-risk steps first (fail-fast)
        optimized_groups = []
        changes = []
        for group in parallel_groups:
            sorted_group = sorted(group, key=lambda s: -risk_per_step.get(s, 0))
            optimized_groups.append(sorted_group)
            if sorted_group != group:
                changes.append(f"Reordered group: {group} -> {sorted_group} (fail-fast)")

        # Determine models to pre-warm
        models_needed = set()
        for step in step_names:
            model = _AGENT_MODEL_MAP.get(step)
            if model:
                models_needed.add(model)

        # Cost forecast
        try:
            forecast = await predictive.get_cost_forecast(step_names)
            total_cost = forecast.get("total_estimated_cost_usd", 0)
            total_duration = forecast.get("total_estimated_duration_sec", 0)
        except Exception:
            total_cost = 0
            total_duration = 0

        return DAGOptimization(
            original_groups=parallel_groups,
            optimized_groups=optimized_groups,
            models_to_prewarm=sorted(models_needed),
            estimated_cost_usd=total_cost,
            estimated_duration_sec=total_duration,
            risk_per_step=risk_per_step,
            changes_made=changes,
        )
