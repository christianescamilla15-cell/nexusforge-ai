"""PlannerAgent — ReAct plan-and-verify with dependency validation."""

import json
import logging

from app.agents.base import BaseAgent, AgentResult, clean_llm_json
from app.agents.registry import register_agent, list_agents

logger = logging.getLogger(__name__)

PLAN_PROMPT = """You are a planning agent using ReAct methodology.
For the given task, create a detailed execution plan.

Available agents and their capabilities: {agents}

Rules:
- Each step must use an available agent
- Dependencies must reference earlier steps only (no cycles)
- Steps with no dependencies can run in parallel
- Mark each step with a priority (high/medium/low)
- Estimate tokens and seconds for each step

Respond ONLY with valid JSON (no markdown):
{{
  "plan": [{{
    "step": <int>,
    "description": "<what to do>",
    "agent": "<agent_type>",
    "dependencies": [<step_numbers>],
    "priority": "<high/medium/low>",
    "estimated_tokens": <int>,
    "estimated_seconds": <float>,
    "can_parallelize": <bool>,
    "fallback_agent": "<agent_type or null>"
  }}],
  "parallel_groups": [[<steps that can run together>]],
  "estimated_steps": <int>,
  "complexity": "<low/medium/high>",
  "reasoning": "<brief explanation of plan design choices>"
}}

Task:
{task}"""

VERIFY_PROMPT = """Verify this execution plan for correctness.
Check:
1. All agent types are valid (available: {agents})
2. Dependencies are acyclic (no step depends on a later step)
3. Parallel groups have no internal dependencies
4. No missing critical steps
5. Fallback agents are valid

Plan: {plan}
Original task: {task}

Respond ONLY with valid JSON:
{{"valid": <bool>, "issues": ["<issue>"], "revised_plan": null}}"""


class PlannerAgent(BaseAgent):
    name = "PlannerAgent"
    agent_type = "planner"
    description = "Decomposes complex tasks into verified execution plans with dependencies and parallelization."

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        task = input_data.get("task", input_data.get("text", ""))
        config = config or {}

        if config.get("demo") or not task:
            return AgentResult(
                output={
                    "plan": [
                        {"step": 1, "description": "Classify document type", "agent": "classifier",
                         "dependencies": [], "priority": "high", "estimated_tokens": 500,
                         "estimated_seconds": 2.0, "can_parallelize": True, "fallback_agent": None},
                        {"step": 2, "description": "Extract entities", "agent": "extractor",
                         "dependencies": [1], "priority": "high", "estimated_tokens": 800,
                         "estimated_seconds": 3.0, "can_parallelize": False, "fallback_agent": None},
                        {"step": 3, "description": "Validate extracted data", "agent": "validator",
                         "dependencies": [2], "priority": "medium", "estimated_tokens": 400,
                         "estimated_seconds": 1.5, "can_parallelize": True, "fallback_agent": None},
                        {"step": 4, "description": "Generate summary", "agent": "summarizer",
                         "dependencies": [2], "priority": "medium", "estimated_tokens": 600,
                         "estimated_seconds": 2.0, "can_parallelize": True, "fallback_agent": None},
                    ],
                    "parallel_groups": [[1], [2], [3, 4]],
                    "estimated_steps": 4,
                    "complexity": "medium",
                    "reasoning": "Demo plan — classify first, then extract, then validate and summarize in parallel.",
                },
                tokens_used=0, cost_usd=0.0,
                provider="local", model="demo",
            )

        available = list_agents()
        total_tokens = 0
        total_cost = 0.0

        # Step 1: Generate plan
        messages = [
            {"role": "system", "content": self._build_system_prompt_v2("Plan task execution using ReAct methodology.")},
            {"role": "user", "content": PLAN_PROMPT.format(agents=", ".join(available), task=task[:2000])},
        ]

        try:
            # Phase 3 Feature 3 — Memory Tool opt-in path (PlannerAgent).
            # When NEXUSFORGE_MEMORY_TOOL_PLANNER=1 is set AND the
            # Anthropic API key is configured, route the plan-generation
            # LLM call through a multi-turn agent loop with the
            # memory_20250818 tool enabled. The agent can then
            # accumulate successful plan templates per complexity tier,
            # validation-failure post-mortems, and parallelization
            # decisions that backfired at runtime (see docs/anthropic-
            # features-research.md §9.2). OFF BY DEFAULT — production
            # behavior is byte-identical to pre-Phase-3. The Step 3
            # verification call below intentionally stays on the legacy
            # path: it is a deterministic check against the current
            # plan and does not benefit from cross-run memory.
            import os as _os
            if _os.environ.get("NEXUSFORGE_MEMORY_TOOL_PLANNER", "0") == "1":
                from app.llm.agent_loop import run_memory_loop_for_agent
                from app.llm.provider import LLMResponse as _LLMResponse
                from app.config import settings as _settings

                api_key = getattr(_settings, "anthropic_api_key", "") or ""
                if not api_key:
                    # No key -> fall back to the legacy router path.
                    resp = await self._resilient_llm_call(
                        messages, temperature=0.3, max_tokens=2048
                    )
                else:
                    # Extract system + non-system messages for the loop.
                    system_content = ""
                    loop_messages: list[dict] = []
                    for _m in messages:
                        if _m.get("role") == "system":
                            system_content = _m.get("content", "")
                        else:
                            loop_messages.append(_m)

                    loop_resp = await run_memory_loop_for_agent(
                        agent_id="PlannerAgent",
                        system=system_content,
                        messages=loop_messages,
                        api_key=api_key,
                        max_tokens=2048,
                        temperature=0.3,
                        max_turns=5,
                    )
                    # Adapt AgentLoopResponse to the LLMResponse shape
                    # so the rest of this method stays unchanged.
                    resp = _LLMResponse(
                        text=loop_resp.text,
                        tokens_input=loop_resp.tokens_input,
                        tokens_output=loop_resp.tokens_output,
                        model=loop_resp.model,
                        provider=loop_resp.provider,
                        cost_usd=loop_resp.cost_usd,
                        thinking=loop_resp.thinking,
                    )
            else:
                # Legacy path — unchanged.
                resp = await self._resilient_llm_call(
                    messages, temperature=0.3, max_tokens=2048
                )

            plan = clean_llm_json(resp.text)
            total_tokens += resp.tokens_input + resp.tokens_output
            total_cost += getattr(resp, "cost_usd", 0.0)
        except Exception as exc:
            logger.warning("PlannerAgent generate failed: %s", exc)
            return AgentResult(
                output={"plan": [], "estimated_steps": 0, "complexity": "unknown", "error": str(exc)},
                tokens_used=0, cost_usd=0.0,
                provider="local", model="fallback",
            )

        # Step 2: Local validation (free, instant)
        local_issues = self._validate_plan_locally(plan, available)
        if local_issues:
            plan["_local_validation_issues"] = local_issues
            logger.info("PlannerAgent local validation found %d issues", len(local_issues))

        # Step 3: LLM verification (only if plan is non-trivial)
        plan_steps = plan.get("plan", [])
        if len(plan_steps) >= 3 and not local_issues:
            try:
                verify_messages = [
                    {"role": "system", "content": "You verify execution plans for correctness."},
                    {"role": "user", "content": VERIFY_PROMPT.format(
                        agents=", ".join(available),
                        plan=json.dumps(plan, indent=2)[:2000],
                        task=task[:500],
                    )},
                ]
                verify_resp = await self._resilient_llm_call(verify_messages, temperature=0.1, max_tokens=512)
                verification = clean_llm_json(verify_resp.text)
                total_tokens += verify_resp.tokens_input + verify_resp.tokens_output
                total_cost += getattr(verify_resp, "cost_usd", 0.0)

                plan["_verified"] = verification.get("valid", False)
                if verification.get("issues"):
                    plan["_verification_issues"] = verification["issues"]
                if verification.get("revised_plan"):
                    plan = verification["revised_plan"]
                    plan["_verified"] = True
            except Exception as exc:
                logger.info("PlannerAgent verification skipped: %s", exc)
                plan["_verified"] = False

        return AgentResult(
            output=plan,
            tokens_used=total_tokens,
            cost_usd=total_cost,
            provider=resp.provider, model=resp.model,
        )

    @staticmethod
    def _validate_plan_locally(plan: dict, available_agents: list[str]) -> list[str]:
        """Deterministic validation — free, instant, no LLM needed."""
        issues = []
        steps = plan.get("plan", [])
        step_numbers = {s.get("step") for s in steps}

        for s in steps:
            agent = s.get("agent", "")
            if agent not in available_agents:
                issues.append(f"Step {s.get('step')}: agent '{agent}' not available")
            for dep in s.get("dependencies", []):
                if dep not in step_numbers:
                    issues.append(f"Step {s.get('step')}: dependency {dep} does not exist")
                if dep >= s.get("step", 0):
                    issues.append(f"Step {s.get('step')}: dependency {dep} is not an earlier step (cycle)")
        return issues


register_agent("planner", PlannerAgent())
