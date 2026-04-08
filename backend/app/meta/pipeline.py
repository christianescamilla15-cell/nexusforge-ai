"""Multi-LLM Execution Pipeline — chains models by their strengths.

Each phase dispatches to a specific Ollama model via the LLM router:
  THINK  → gemma (reasoning with thinking mode)
  BUILD  → qwen2.5-coder (structured output)
  DOCUMENT → llama3.1 (narrative text)
  VERIFY → deepseek-r1 (critical review with thinking)

Phases are composable: caller specifies which to run.
Each phase receives the output of the previous phase.
"""

import logging
import time
from typing import Any

from app.meta.schemas import (
    PipelinePhase, PhaseResult, PipelineResult,
    PHASE_MODEL_MAP, THINKING_PHASES, MetaPipelineRequest,
)

logger = logging.getLogger(__name__)

# System prompts per phase
PHASE_SYSTEM_PROMPTS = {
    PipelinePhase.THINK: (
        "You are a senior architect reasoning about a technical problem. "
        "Think step by step. Consider trade-offs, risks, and alternatives. "
        "Output a structured analysis with clear sections."
    ),
    PipelinePhase.BUILD: (
        "You are a senior developer generating precise, production-ready output. "
        "Follow existing code patterns. Output clean, structured content (code, JSON, markdown). "
        "No explanations unless asked — just the deliverable."
    ),
    PipelinePhase.DOCUMENT: (
        "You are a technical writer creating clear documentation. "
        "Write for developers who are new to the project. "
        "Use concrete examples. Keep it concise but complete."
    ),
    PipelinePhase.VERIFY: (
        "You are a critical code reviewer. Your job is to find problems. "
        "Check: correctness, security, performance, missing edge cases. "
        "For each issue found, state the file/location, severity, and suggested fix. "
        "If everything looks good, say so explicitly."
    ),
    PipelinePhase.PREDICT: (
        "You are a data analyst predicting future needs based on patterns. "
        "Analyze the provided data and output structured predictions. "
        "Each prediction must have: title, priority, rationale, affected areas."
    ),
}


class MetaPipeline:
    """Multi-LLM pipeline engine that chains models by phase.

    Usage:
        pipeline = MetaPipeline()
        result = await pipeline.run(
            prompt="Design a caching layer for the API",
            phases=[PipelinePhase.THINK, PipelinePhase.BUILD, PipelinePhase.VERIFY],
        )
    """

    def __init__(self):
        self._router = None

    def _get_router(self):
        if self._router is None:
            from app.llm.router import get_router
            self._router = get_router()
        return self._router

    async def run(
        self,
        prompt: str,
        phases: list[PipelinePhase] | None = None,
        context: dict[str, Any] | None = None,
        max_tokens: int = 2048,
    ) -> PipelineResult:
        """Execute a multi-phase pipeline, chaining outputs between phases."""

        if phases is None:
            phases = [PipelinePhase.THINK, PipelinePhase.BUILD]

        result = PipelineResult()
        current_input = prompt

        # Add context to the initial prompt if provided
        if context:
            context_str = "\n".join(f"**{k}**: {v}" for k, v in context.items() if v)
            if context_str:
                current_input = f"{context_str}\n\n---\n\n{current_input}"

        for phase in phases:
            try:
                phase_result = await self._run_phase(
                    phase=phase,
                    input_text=current_input,
                    original_prompt=prompt,
                    max_tokens=max_tokens,
                )
                result.add_phase(phase_result)

                # Chain: next phase receives this phase's output
                current_input = self._build_chain_prompt(phase, phase_result, prompt)

            except Exception as e:
                logger.error("MetaPipeline phase %s failed: %s", phase.value, e)
                result.add_phase(PhaseResult(
                    phase=phase,
                    model=PHASE_MODEL_MAP.get(phase, "unknown"),
                    output=f"Phase failed: {e}",
                ))
                break  # Don't continue pipeline if a phase fails

        return result

    async def run_single(
        self,
        prompt: str,
        phase: PipelinePhase,
        max_tokens: int = 2048,
    ) -> PhaseResult:
        """Run a single phase (no chaining)."""
        return await self._run_phase(phase, prompt, prompt, max_tokens)

    async def _run_phase(
        self,
        phase: PipelinePhase,
        input_text: str,
        original_prompt: str,
        max_tokens: int,
    ) -> PhaseResult:
        """Execute one phase using the assigned model."""
        router = self._get_router()
        model = PHASE_MODEL_MAP[phase]
        system_prompt = PHASE_SYSTEM_PROMPTS[phase]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text},
        ]

        # Use a synthetic agent name so the router picks the right model
        agent_name = f"Meta{phase.value.capitalize()}Agent"

        start = time.monotonic()

        response = await router.chat(
            messages=messages,
            temperature=0.3 if phase == PipelinePhase.BUILD else 0.5,
            max_tokens=max_tokens,
            agent_name=agent_name,
        )

        duration = time.monotonic() - start

        return PhaseResult(
            phase=phase,
            model=response.model,
            output=response.text,
            thinking=response.thinking,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            duration_sec=round(duration, 2),
            cost_usd=response.cost_usd,
        )

    def _build_chain_prompt(
        self, phase: PipelinePhase, result: PhaseResult, original_prompt: str
    ) -> str:
        """Build the input for the next phase based on current phase output."""
        if phase == PipelinePhase.THINK:
            return (
                f"Based on this analysis, implement the solution:\n\n"
                f"## Original Request\n{original_prompt}\n\n"
                f"## Architecture Analysis\n{result.output}"
            )
        elif phase == PipelinePhase.BUILD:
            return (
                f"Review the following implementation for correctness, security, "
                f"and completeness:\n\n"
                f"## Original Request\n{original_prompt}\n\n"
                f"## Implementation\n{result.output}"
            )
        elif phase == PipelinePhase.VERIFY:
            return (
                f"Document the following based on the review feedback:\n\n"
                f"## Original Request\n{original_prompt}\n\n"
                f"## Review Feedback\n{result.output}"
            )
        else:
            return f"Continue based on:\n\n{result.output}"


# ── Module-level singleton ───────────────────────────────────────────────────

_pipeline: MetaPipeline | None = None


def get_pipeline() -> MetaPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = MetaPipeline()
    return _pipeline
