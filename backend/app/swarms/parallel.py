"""ParallelSwarm — fan-out / fan-in: all agents run simultaneously."""

import asyncio
import logging
import time

from app.agents.registry import get_agent
from app.swarms.base import BaseSwarm, SwarmResult

logger = logging.getLogger(__name__)


class ParallelSwarm(BaseSwarm):
    name = "ParallelSwarm"
    topology = "parallel"

    async def execute(
        self,
        input_data: dict,
        agent_types: list[str],
        config: dict = None,
    ) -> SwarmResult:
        config = config or {}
        start = time.monotonic()

        async def _run_agent(agent_type: str) -> tuple[str, dict, int, float]:
            agent = get_agent(agent_type)
            result = await agent.execute(input_data, config)
            return agent_type, result.output, result.tokens_used, result.cost_usd

        # Fan-out: run all agents in parallel
        tasks = [_run_agent(at) for at in agent_types]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Fan-in: collect results
        combined_output = {}
        total_tokens = 0
        total_cost = 0.0
        agents_used = []
        steps_executed = 0

        for i, result in enumerate(results):
            agent_type = agent_types[i]
            if isinstance(result, Exception):
                logger.warning("ParallelSwarm: agent '%s' failed: %s", agent_type, result)
                combined_output[agent_type] = {"error": str(result)}
            else:
                at, output, tokens, cost = result
                combined_output[at] = output
                total_tokens += tokens
                total_cost += cost
                agents_used.append(at)
                steps_executed += 1

        duration_ms = int((time.monotonic() - start) * 1000)

        return SwarmResult(
            output=combined_output,
            topology=self.topology,
            agents_used=agents_used,
            total_tokens=total_tokens,
            total_cost=total_cost,
            steps_executed=steps_executed,
            duration_ms=duration_ms,
        )
