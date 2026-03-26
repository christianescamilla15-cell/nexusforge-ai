"""DebateSwarm — produce, critique, refine loop."""

import json
import logging
import time

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import get_agent, register_agent
from app.llm.router import get_router
from app.swarms.base import BaseSwarm, SwarmResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CriticAgent — scores and gives feedback
# ---------------------------------------------------------------------------

CRITIC_PROMPT = """You are a strict quality critic. Score the following output from 0-100
and provide specific, actionable feedback for improvement.

Original task input:
{task_input}

Output to evaluate:
{output}

Respond ONLY with valid JSON (no markdown):
{{
  "score": <0-100>,
  "feedback": "<specific improvement suggestions>",
  "strengths": ["..."],
  "weaknesses": ["..."]
}}"""


class CriticAgent(BaseAgent):
    name = "CriticAgent"
    agent_type = "critic"
    description = "Evaluates agent outputs and provides quality scores and feedback."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        config = config or {}
        output_text = json.dumps(input_data.get("_output_to_evaluate", {}), default=str)[:3000]
        task_input = json.dumps(
            {k: v for k, v in input_data.items() if not k.startswith("_")}, default=str
        )[:2000]

        if config.get("demo"):
            return AgentResult(
                output={"score": 75, "feedback": "Demo feedback", "strengths": [], "weaknesses": []},
                provider="local", model="none",
            )

        messages = [
            {"role": "system", "content": self._build_system_prompt("Critically evaluate outputs.")},
            {"role": "user", "content": CRITIC_PROMPT.format(task_input=task_input, output=output_text)},
        ]

        try:
            router = get_router()
            resp = await router.chat(messages, temperature=0.3, max_tokens=512)
            parsed = json.loads(resp.text)
            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider,
                model=resp.model,
            )
        except Exception as exc:
            logger.warning("CriticAgent fallback: %s", exc)
            return AgentResult(
                output={"score": 50, "feedback": "Unable to evaluate", "strengths": [], "weaknesses": []},
                provider="local", model="fallback",
            )


try:
    get_agent("critic")
except ValueError:
    register_agent("critic", CriticAgent())


# ---------------------------------------------------------------------------
# DebateSwarm
# ---------------------------------------------------------------------------

class DebateSwarm(BaseSwarm):
    name = "DebateSwarm"
    topology = "debate"

    async def execute(
        self,
        input_data: dict,
        agent_types: list[str],
        config: dict = None,
    ) -> SwarmResult:
        config = config or {}
        threshold = config.get("quality_threshold", 70)
        max_iterations = config.get("max_iterations", 3)
        start = time.monotonic()

        total_tokens = 0
        total_cost = 0.0
        agents_used = []
        steps_executed = 0
        iteration_scores = []

        # Use first agent as the producer
        producer_type = agent_types[0] if agent_types else "analyzer"
        producer = get_agent(producer_type)
        critic = get_agent("critic")

        current_input = dict(input_data)
        last_output = {}

        for iteration in range(max_iterations):
            # Producer generates output
            prod_result = await producer.execute(current_input, config)
            total_tokens += prod_result.tokens_used
            total_cost += prod_result.cost_usd
            steps_executed += 1
            if producer_type not in agents_used:
                agents_used.append(producer_type)
            last_output = prod_result.output

            # Critic evaluates
            critic_input = {**input_data, "_output_to_evaluate": prod_result.output}
            critic_result = await critic.execute(critic_input, config)
            total_tokens += critic_result.tokens_used
            total_cost += critic_result.cost_usd
            steps_executed += 1
            if "critic" not in agents_used:
                agents_used.append("critic")

            score = critic_result.output.get("score", 0)
            feedback = critic_result.output.get("feedback", "")
            iteration_scores.append(score)

            logger.info(
                "DebateSwarm iteration %d: score=%d, threshold=%d",
                iteration + 1, score, threshold,
            )

            if score >= threshold:
                break

            # Feed critic's feedback back into producer input for next iteration
            current_input = {
                **input_data,
                "_previous_output": prod_result.output,
                "_critic_feedback": feedback,
                "_critic_score": score,
                "_iteration": iteration + 1,
            }

        duration_ms = int((time.monotonic() - start) * 1000)

        return SwarmResult(
            output={
                **last_output,
                "_debate_iterations": len(iteration_scores),
                "_iteration_scores": iteration_scores,
                "_final_score": iteration_scores[-1] if iteration_scores else 0,
            },
            topology=self.topology,
            agents_used=agents_used,
            total_tokens=total_tokens,
            total_cost=total_cost,
            steps_executed=steps_executed,
            duration_ms=duration_ms,
        )
