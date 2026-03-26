"""SequentialSwarm — executes agents one after another: A -> B -> C."""

import logging
import time

from app.agents.registry import get_agent
from app.swarms.base import BaseSwarm, SwarmResult

logger = logging.getLogger(__name__)


class SequentialSwarm(BaseSwarm):
    name = "SequentialSwarm"
    topology = "sequential"

    async def execute(
        self,
        input_data: dict,
        agent_types: list[str],
        config: dict = None,
    ) -> SwarmResult:
        config = config or {}
        start = time.monotonic()

        total_tokens = 0
        total_cost = 0.0
        steps_executed = 0
        agents_used = []
        current_input = dict(input_data)
        last_output = {}

        for agent_type in agent_types:
            try:
                agent = get_agent(agent_type)
                result = await agent.execute(current_input, config)

                total_tokens += result.tokens_used
                total_cost += result.cost_usd
                steps_executed += 1
                agents_used.append(agent_type)
                last_output = result.output

                # Output of this agent becomes input of next
                current_input = {**input_data, **result.output}

            except Exception as exc:
                logger.warning("SequentialSwarm: agent '%s' failed: %s", agent_type, exc)
                last_output = {
                    "error": str(exc),
                    "failed_agent": agent_type,
                    "partial_results": last_output,
                }
                break

        duration_ms = int((time.monotonic() - start) * 1000)

        return SwarmResult(
            output=last_output,
            topology=self.topology,
            agents_used=agents_used,
            total_tokens=total_tokens,
            total_cost=total_cost,
            steps_executed=steps_executed,
            duration_ms=duration_ms,
        )
