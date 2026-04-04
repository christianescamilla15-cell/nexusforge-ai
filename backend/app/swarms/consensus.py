"""ConsensusSwarm — N agents independently analyze, judge uses Weighted Borda Count."""

import asyncio
import json
import logging
import time

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import get_agent, register_agent
from app.swarms.base import BaseSwarm, SwarmResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JudgeAgent — Weighted Borda Count + LLM ranking
# ---------------------------------------------------------------------------

JUDGE_PROMPT = """You are an impartial judge. Multiple agents have independently analyzed the same input.
RANK all outputs from best to worst. Do NOT just pick one — provide a full ranking.

Task input:
{task_input}

Agent outputs:
{outputs}

Respond ONLY with valid JSON (no markdown):
{{
  "ranking": [
    {{"rank": 1, "agent": "<best agent_type>", "quality": <0-100>, "strengths": "<brief>"}},
    {{"rank": 2, "agent": "<second best>", "quality": <0-100>, "strengths": "<brief>"}},
    ...
  ],
  "consensus_output": {{<synthesized best answer combining top insights>}},
  "reasoning": "<why this ranking was chosen>"
}}"""


def _weighted_borda_score(rankings: list[dict], n_agents: int) -> dict[str, float]:
    """Compute Confidence-Weighted Borda scores from LLM rankings.

    score(agent) = (N - rank_position) * (quality / 100)

    Returns dict of agent_type -> score, sorted descending.
    """
    scores: dict[str, float] = {}
    for entry in rankings:
        agent = entry.get("agent", "")
        rank = entry.get("rank", n_agents)
        quality = entry.get("quality", 50) / 100.0
        borda_points = max(0, n_agents - rank + 1)
        scores[agent] = borda_points * quality

    # Normalize to 0-100
    max_score = max(scores.values()) if scores else 1
    if max_score > 0:
        scores = {k: round(v / max_score * 100, 1) for k, v in scores.items()}

    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


class JudgeAgent(BaseAgent):
    name = "JudgeAgent"
    agent_type = "judge"
    description = "Evaluates multiple agent outputs using Weighted Borda Count ranking."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        config = config or {}
        agent_outputs = input_data.get("_agent_outputs", {})
        task_input = json.dumps(
            {k: v for k, v in input_data.items() if not k.startswith("_")}, default=str
        )[:2000]

        agents = list(agent_outputs.keys())

        if config.get("demo") or not agents:
            winner = agents[0] if agents else "none"
            return AgentResult(
                output={
                    "winner": winner,
                    "consensus_output": agent_outputs.get(winner, {}),
                    "reasoning": "Demo mode selection",
                    "ranking": [{"rank": i + 1, "agent": a, "quality": 70} for i, a in enumerate(agents)],
                    "borda_scores": {a: 70 for a in agents},
                },
                provider="local", model="demo",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Judge and RANK agent outputs fairly.")},
            {"role": "user", "content": JUDGE_PROMPT.format(
                task_input=task_input,
                outputs=json.dumps(agent_outputs, default=str)[:4000],
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.2, max_tokens=1024)
            parsed = json.loads(resp.text)

            # Compute Weighted Borda scores from LLM ranking
            ranking = parsed.get("ranking", [])
            borda_scores = _weighted_borda_score(ranking, len(agents))

            # Winner is highest Borda score
            winner = next(iter(borda_scores)) if borda_scores else (agents[0] if agents else "none")

            return AgentResult(
                output={
                    "winner": winner,
                    "consensus_output": parsed.get("consensus_output", agent_outputs.get(winner, {})),
                    "reasoning": parsed.get("reasoning", ""),
                    "ranking": ranking,
                    "borda_scores": borda_scores,
                },
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("JudgeAgent fallback: %s", exc)
            winner = agents[0] if agents else "none"
            return AgentResult(
                output={
                    "winner": winner,
                    "consensus_output": agent_outputs.get(winner, {}),
                    "reasoning": f"Fallback selection: {exc}",
                    "ranking": [{"rank": i + 1, "agent": a, "quality": 50} for i, a in enumerate(agents)],
                    "borda_scores": {a: 50 for a in agents},
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

        # Step 2: Judge ranks all outputs using Weighted Borda Count
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
