"""ConsensusSwarm — N agents independently analyze, judge picks the best."""

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
# JudgeAgent — picks the best output or synthesizes consensus
# ---------------------------------------------------------------------------

JUDGE_PROMPT = """You are an impartial judge. Multiple agents have independently analyzed the same input.
Review their outputs and either pick the best one or synthesize a consensus answer.

Task input:
{task_input}

Agent outputs:
{outputs}

Respond ONLY with valid JSON (no markdown):
{{
  "winner": "<agent_type that produced the best output, or 'consensus'>",
  "consensus_output": {{<synthesized best answer>}},
  "reasoning": "<why this was chosen>",
  "votes": [
    {{"agent": "<type>", "quality": <0-100>}}
  ]
}}"""


class JudgeAgent(BaseAgent):
    name = "JudgeAgent"
    agent_type = "judge"
    description = "Evaluates multiple agent outputs and picks the best or synthesizes consensus."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        config = config or {}
        agent_outputs = input_data.get("_agent_outputs", {})
        task_input = json.dumps(
            {k: v for k, v in input_data.items() if not k.startswith("_")}, default=str
        )[:2000]

        if config.get("demo"):
            agents = list(agent_outputs.keys())
            winner = agents[0] if agents else "none"
            return AgentResult(
                output={
                    "winner": winner,
                    "consensus_output": agent_outputs.get(winner, {}),
                    "reasoning": "Demo mode selection",
                    "votes": [{"agent": a, "quality": 70} for a in agents],
                },
                provider="local", model="none",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Judge agent outputs fairly.")},
            {"role": "user", "content": JUDGE_PROMPT.format(
                task_input=task_input,
                outputs=json.dumps(agent_outputs, default=str)[:4000],
            )},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.2, max_tokens=1024)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("JudgeAgent fallback: %s", exc)
            # Fallback: pick the first agent's output
            agents = list(agent_outputs.keys())
            winner = agents[0] if agents else "none"
            return AgentResult(
                output={
                    "winner": winner,
                    "consensus_output": agent_outputs.get(winner, {}),
                    "reasoning": f"Fallback selection: {exc}",
                    "votes": [{"agent": a, "quality": 50} for a in agents],
                },
                provider="local", model="fallback",
            )


try:
    get_agent("judge")
except ValueError:
    register_agent("judge", JudgeAgent())


# ---------------------------------------------------------------------------
# ConsensusSwarm
# ---------------------------------------------------------------------------

class ConsensusSwarm(BaseSwarm):
    name = "ConsensusSwarm"
    topology = "consensus"

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

        # Step 1: All agents independently analyze the same input (fan-out)
        async def _run_agent(agent_type: str):
            agent = get_agent(agent_type)
            return agent_type, await agent.execute(input_data, config)

        tasks = [_run_agent(at) for at in agent_types]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        agent_outputs = {}
        for i, res in enumerate(results):
            at = agent_types[i]
            if isinstance(res, Exception):
                logger.warning("ConsensusSwarm agent '%s' failed: %s", at, res)
                agent_outputs[at] = {"error": str(res)}
            else:
                agent_type, agent_result = res
                agent_outputs[agent_type] = agent_result.output
                total_tokens += agent_result.tokens_used
                total_cost += agent_result.cost_usd
                agents_used.append(agent_type)
                steps_executed += 1

        # Step 2: Judge picks the best or synthesizes consensus
        judge = get_agent("judge")
        judge_input = {**input_data, "_agent_outputs": agent_outputs}
        judge_result = await judge.execute(judge_input, config)
        total_tokens += judge_result.tokens_used
        total_cost += judge_result.cost_usd
        agents_used.append("judge")
        steps_executed += 1

        duration_ms = int((time.monotonic() - start) * 1000)

        return SwarmResult(
            output={
                **judge_result.output,
                "all_agent_outputs": agent_outputs,
            },
            topology=self.topology,
            agents_used=agents_used,
            total_tokens=total_tokens,
            total_cost=total_cost,
            steps_executed=steps_executed,
            duration_ms=duration_ms,
        )
