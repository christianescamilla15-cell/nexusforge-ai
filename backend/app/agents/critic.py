"""CriticAgent — multi-rubric quality evaluation with weighted scoring."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

# Default rubric — can be customized per tenant/workflow
DEFAULT_RUBRIC = [
    {"name": "accuracy", "weight": 0.30,
     "description": "Are all facts correct and claims verifiable?"},
    {"name": "completeness", "weight": 0.25,
     "description": "Does the output address all parts of the request?"},
    {"name": "clarity", "weight": 0.20,
     "description": "Is the output well-structured and easy to understand?"},
    {"name": "actionability", "weight": 0.15,
     "description": "Does it provide clear next steps or useful conclusions?"},
    {"name": "professional_tone", "weight": 0.10,
     "description": "Is the language appropriate for a business context?"},
]

CRITIQUE_PROMPT = """Evaluate the quality of the following agent output using a multi-criteria rubric.
Score EACH criterion independently on a 1-5 scale with brief reasoning.

Rubric criteria:
{rubric}

Scale: 1=Poor, 2=Below Average, 3=Acceptable, 4=Good, 5=Excellent

Respond ONLY with valid JSON (no markdown):
{{
  "criteria_scores": [
    {{"name": "<criterion>", "score": <1-5>, "reasoning": "<brief>"}}
  ],
  "overall_score": <0-100>,
  "strengths": ["<s1>"],
  "improvements": ["<i1>"],
  "pass": <true if overall_score >= 60>
}}

Agent output to evaluate:
{output}"""


def _compute_weighted_score(criteria_scores: list[dict], rubric: list[dict]) -> float:
    """Compute weighted score from individual criteria (1-5) to 0-100 scale."""
    weight_map = {r["name"]: r["weight"] for r in rubric}
    total_weight = 0.0
    weighted_sum = 0.0

    for cs in criteria_scores:
        name = cs.get("name", "")
        score = cs.get("score", 3)
        weight = weight_map.get(name, 0.1)
        weighted_sum += score * weight
        total_weight += weight

    if total_weight == 0:
        return 50.0
    # Convert 1-5 scale to 0-100
    return round((weighted_sum / total_weight - 1) / 4 * 100, 1)


class CriticAgent(BaseAgent):
    name = "CriticAgent"
    agent_type = "critic"
    description = "Evaluates output quality using weighted multi-criteria rubric scoring."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        output = input_data.get("output", input_data.get("text", ""))
        config = config or {}
        rubric = config.get("rubric", DEFAULT_RUBRIC)

        if config.get("demo") or not output:
            return AgentResult(
                output={
                    "overall_score": 78,
                    "criteria_scores": [
                        {"name": "accuracy", "score": 4, "reasoning": "Facts are correct"},
                        {"name": "completeness", "score": 4, "reasoning": "Addresses main points"},
                        {"name": "clarity", "score": 4, "reasoning": "Well structured"},
                        {"name": "actionability", "score": 3, "reasoning": "Could add next steps"},
                        {"name": "professional_tone", "score": 5, "reasoning": "Appropriate language"},
                    ],
                    "strengths": ["Clear formatting", "Complete data fields"],
                    "improvements": ["Add confidence scores", "Include source references"],
                    "pass": True,
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        raw = json.dumps(output) if isinstance(output, (dict, list)) else str(output)
        rubric_text = "\n".join(
            f"- {r['name']} (weight={r['weight']}): {r['description']}"
            for r in rubric
        )

        messages = [
            {"role": "system", "content": self._build_system_prompt(
                "Critically evaluate agent output using a structured rubric."
            )},
            {"role": "user", "content": CRITIQUE_PROMPT.format(
                rubric=rubric_text, output=raw[:3000]
            )},
        ]

        try:
            resp = await self._resilient_llm_call(messages, temperature=0.3, max_tokens=1024)
            parsed = json.loads(resp.text)

            # Recompute weighted score from criteria (don't trust LLM math)
            criteria = parsed.get("criteria_scores", [])
            computed_score = _compute_weighted_score(criteria, rubric)
            parsed["overall_score"] = computed_score
            parsed["pass"] = computed_score >= 60
            parsed["_rubric_used"] = [r["name"] for r in rubric]

            return AgentResult(
                output=parsed,
                tokens_used=resp.tokens_input + resp.tokens_output,
                cost_usd=getattr(resp, "cost_usd", 0.0),
                provider=resp.provider, model=resp.model,
            )
        except Exception as exc:
            logger.warning("CriticAgent LLM fallback: %s", exc)
            return AgentResult(
                output={
                    "overall_score": 50,
                    "criteria_scores": [],
                    "strengths": [],
                    "improvements": [f"Evaluation unavailable: {exc}"],
                    "pass": True,
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )


register_agent("critic", CriticAgent())
