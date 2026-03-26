"""HierarchicalSwarm — manager decomposes task, delegates to workers, synthesizes."""

import asyncio
import json
import logging
import time

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import get_agent, register_agent
from app.llm.router import get_router
from app.swarms.base import BaseSwarm, SwarmResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PlannerAgent — internal manager agent for task decomposition / synthesis
# ---------------------------------------------------------------------------

PLAN_PROMPT = """You are a manager agent. Given the task below and a list of available worker agents,
decompose the task into subtasks — one per worker agent.

Available agents: {agents}

Task input:
{input_data}

Respond ONLY with valid JSON (no markdown):
{{
  "subtasks": [
    {{"agent": "<agent_type>", "input": {{...}} }}
  ]
}}"""

SYNTHESIZE_PROMPT = """You are a manager agent. Synthesize the worker results into a single coherent output.

Worker results:
{results}

Respond ONLY with valid JSON (no markdown):
{{
  "synthesis": "<combined summary>",
  "key_findings": ["..."],
  "confidence": <0-100>
}}"""


class PlannerAgent(BaseAgent):
    name = "PlannerAgent"
    agent_type = "planner"
    description = "Decomposes tasks and synthesizes results from worker agents."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        config = config or {}
        mode = input_data.get("_planner_mode", "plan")

        if config.get("demo"):
            if mode == "synthesize":
                return AgentResult(
                    output={"synthesis": "Demo synthesis", "key_findings": [], "confidence": 80},
                    provider="local", model="none",
                )
            agents = input_data.get("_agents", [])
            return AgentResult(
                output={"subtasks": [{"agent": a, "input": input_data} for a in agents]},
                provider="local", model="none",
            )

        if mode == "synthesize":
            prompt = SYNTHESIZE_PROMPT.format(
                results=json.dumps(input_data.get("_worker_results", {}), default=str)[:4000],
            )
        else:
            prompt = PLAN_PROMPT.format(
                agents=", ".join(input_data.get("_agents", [])),
                input_data=json.dumps({k: v for k, v in input_data.items() if not k.startswith("_")}, default=str)[:3000],
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Manage and coordinate agent tasks.")},
            {"role": "user", "content": prompt},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.3, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("PlannerAgent fallback: %s", exc)
            agents = input_data.get("_agents", [])
            if mode == "synthesize":
                return AgentResult(
                    output={"synthesis": "Could not synthesize", "key_findings": [], "confidence": 0},
                    provider="local", model="fallback",
                )
            return AgentResult(
                output={"subtasks": [{"agent": a, "input": input_data} for a in agents]},
                provider="local", model="fallback",
            )


# Register planner only once
try:
    get_agent("planner")
except ValueError:
    register_agent("planner", PlannerAgent())


# ---------------------------------------------------------------------------
# HierarchicalSwarm
# ---------------------------------------------------------------------------

class HierarchicalSwarm(BaseSwarm):
    name = "HierarchicalSwarm"
    topology = "hierarchical"

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
        agents_used = []
        steps_executed = 0

        # Step 1: Manager decomposes task
        planner = get_agent("planner")
        plan_input = {**input_data, "_planner_mode": "plan", "_agents": agent_types}
        plan_result = await planner.execute(plan_input, config)
        total_tokens += plan_result.tokens_used
        total_cost += plan_result.cost_usd
        steps_executed += 1
        agents_used.append("planner")

        subtasks = plan_result.output.get("subtasks", [])

        # Step 2: Delegate subtasks to workers in parallel
        async def _run_worker(subtask: dict):
            agent_type = subtask.get("agent", "")
            sub_input = subtask.get("input", input_data)
            # Ensure base input is merged
            merged = {**input_data, **sub_input} if isinstance(sub_input, dict) else dict(input_data)
            agent = get_agent(agent_type)
            return agent_type, await agent.execute(merged, config)

        worker_tasks = [_run_worker(st) for st in subtasks]
        worker_results_raw = await asyncio.gather(*worker_tasks, return_exceptions=True)

        worker_outputs = {}
        for i, res in enumerate(worker_results_raw):
            at = subtasks[i].get("agent", f"worker_{i}")
            if isinstance(res, Exception):
                logger.warning("HierarchicalSwarm worker '%s' failed: %s", at, res)
                worker_outputs[at] = {"error": str(res)}
            else:
                agent_type, agent_result = res
                worker_outputs[agent_type] = agent_result.output
                total_tokens += agent_result.tokens_used
                total_cost += agent_result.cost_usd
                agents_used.append(agent_type)
                steps_executed += 1

        # Step 3: Manager synthesizes results
        synth_input = {**input_data, "_planner_mode": "synthesize", "_worker_results": worker_outputs}
        synth_result = await planner.execute(synth_input, config)
        total_tokens += synth_result.tokens_used
        total_cost += synth_result.cost_usd
        steps_executed += 1

        duration_ms = int((time.monotonic() - start) * 1000)

        return SwarmResult(
            output={**synth_result.output, "worker_outputs": worker_outputs},
            topology=self.topology,
            agents_used=agents_used,
            total_tokens=total_tokens,
            total_cost=total_cost,
            steps_executed=steps_executed,
            duration_ms=duration_ms,
        )
