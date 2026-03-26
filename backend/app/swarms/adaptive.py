"""AdaptiveSwarm — router picks the best topology, retries if quality is low."""

import json
import logging
import time

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import get_agent, register_agent
from app.llm.router import get_router
from app.swarms.base import BaseSwarm, SwarmResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RouterAgent — analyzes input to recommend a topology
# ---------------------------------------------------------------------------

ROUTER_PROMPT = """You are a routing agent. Given the task input and available topologies,
decide which swarm topology is best suited for this task.

Available topologies: sequential, parallel, hierarchical, debate, consensus
Available agents: {agents}

Task input:
{input_data}

Consider:
- sequential: for step-by-step pipelines where order matters
- parallel: for independent analyses that can run simultaneously
- hierarchical: for complex tasks that need decomposition by a manager
- debate: for tasks requiring quality refinement through critique
- consensus: for tasks where multiple perspectives improve accuracy

Respond ONLY with valid JSON (no markdown):
{{
  "recommended_topology": "<topology_name>",
  "reasoning": "<why this topology>",
  "confidence": <0-100>,
  "agent_order": ["<agent1>", "<agent2>"]
}}"""


class RouterAgent(BaseAgent):
    name = "RouterAgent"
    agent_type = "router"
    description = "Analyzes input to recommend the best swarm topology."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        config = config or {}
        agents = input_data.get("_agents", [])
        task_input = json.dumps(
            {k: v for k, v in input_data.items() if not k.startswith("_")}, default=str
        )[:3000]

        if config.get("demo"):
            # Simple heuristic for demo mode
            n = len(agents)
            if n <= 1:
                topo = "sequential"
            elif n == 2:
                topo = "debate"
            elif n >= 4:
                topo = "hierarchical"
            else:
                topo = "parallel"
            return AgentResult(
                output={
                    "recommended_topology": topo,
                    "reasoning": f"Demo heuristic: {n} agents -> {topo}",
                    "confidence": 70,
                    "agent_order": agents,
                },
                provider="local", model="none",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Route tasks to optimal topology.")},
            {"role": "user", "content": ROUTER_PROMPT.format(
                agents=", ".join(agents),
                input_data=task_input,
            )},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=512)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("RouterAgent fallback: %s", exc)
            return AgentResult(
                output={
                    "recommended_topology": "parallel",
                    "reasoning": f"Fallback due to error: {exc}",
                    "confidence": 30,
                    "agent_order": agents,
                },
                provider="local", model="fallback",
            )


try:
    get_agent("router")
except ValueError:
    register_agent("router", RouterAgent())


# ---------------------------------------------------------------------------
# AdaptiveSwarm
# ---------------------------------------------------------------------------

# Topology history for learning which topologies work best
_topology_log: list[dict] = []

# Avoid circular import: topologies are resolved at runtime from manager
FALLBACK_ORDER = ["parallel", "sequential", "hierarchical", "debate", "consensus"]


class AdaptiveSwarm(BaseSwarm):
    name = "AdaptiveSwarm"
    topology = "adaptive"

    async def execute(
        self,
        input_data: dict,
        agent_types: list[str],
        config: dict = None,
    ) -> SwarmResult:
        config = config or {}
        quality_threshold = config.get("quality_threshold", 60)
        start = time.monotonic()

        total_tokens = 0
        total_cost = 0.0

        # Step 1: Router recommends topology
        router_agent = get_agent("router")
        router_input = {**input_data, "_agents": agent_types}
        router_result = await router_agent.execute(router_input, config)
        total_tokens += router_result.tokens_used
        total_cost += router_result.cost_usd

        recommended = router_result.output.get("recommended_topology", "parallel")
        agent_order = router_result.output.get("agent_order", agent_types)

        # Step 2: Execute recommended topology
        from app.swarms.manager import get_swarm  # deferred import to avoid circular

        tried_topologies = []

        for attempt_topo in [recommended] + [t for t in FALLBACK_ORDER if t != recommended]:
            if attempt_topo in tried_topologies:
                continue
            tried_topologies.append(attempt_topo)

            try:
                swarm = get_swarm(attempt_topo)
                result = swarm_result = await swarm.execute(input_data, agent_order, config)
                total_tokens += swarm_result.total_tokens
                total_cost += swarm_result.total_cost

                # Check quality via critic if available
                quality_score = 100  # default: assume good
                try:
                    critic = get_agent("critic")
                    critic_input = {**input_data, "_output_to_evaluate": swarm_result.output}
                    critic_result = await critic.execute(critic_input, config)
                    quality_score = critic_result.output.get("score", 100)
                    total_tokens += critic_result.tokens_used
                    total_cost += critic_result.cost_usd
                except ValueError:
                    pass  # No critic agent registered

                # Log for learning
                _topology_log.append({
                    "topology": attempt_topo,
                    "quality_score": quality_score,
                    "input_keys": list(input_data.keys()),
                    "agent_types": agent_types,
                })

                if quality_score >= quality_threshold:
                    duration_ms = int((time.monotonic() - start) * 1000)
                    return SwarmResult(
                        output={
                            **swarm_result.output,
                            "_adaptive_topology_used": attempt_topo,
                            "_adaptive_quality_score": quality_score,
                            "_adaptive_attempts": len(tried_topologies),
                            "_router_recommendation": recommended,
                        },
                        topology=self.topology,
                        agents_used=["router"] + swarm_result.agents_used,
                        total_tokens=total_tokens,
                        total_cost=total_cost,
                        steps_executed=swarm_result.steps_executed + 1,
                        duration_ms=duration_ms,
                    )

                logger.info(
                    "AdaptiveSwarm: topology '%s' scored %d < %d, trying next",
                    attempt_topo, quality_score, quality_threshold,
                )

            except Exception as exc:
                logger.warning("AdaptiveSwarm: topology '%s' failed: %s", attempt_topo, exc)
                continue

        # All topologies exhausted — return last result
        duration_ms = int((time.monotonic() - start) * 1000)
        last = swarm_result if 'swarm_result' in dir() else SwarmResult(output={}, topology="adaptive")

        return SwarmResult(
            output={
                **(last.output if hasattr(last, 'output') else {}),
                "_adaptive_topology_used": tried_topologies[-1] if tried_topologies else "none",
                "_adaptive_quality_score": quality_score if 'quality_score' in dir() else 0,
                "_adaptive_attempts": len(tried_topologies),
                "_adaptive_exhausted": True,
            },
            topology=self.topology,
            agents_used=["router"] + (last.agents_used if hasattr(last, 'agents_used') else []),
            total_tokens=total_tokens,
            total_cost=total_cost,
            steps_executed=len(tried_topologies) + 1,
            duration_ms=duration_ms,
        )
