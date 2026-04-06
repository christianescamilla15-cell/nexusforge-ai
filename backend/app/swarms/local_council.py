"""LocalCouncil — second opinion engine using local models in parallel.

Runs qwen2.5-coder:7b and llama3.1:8b simultaneously on the same problem.
Returns both perspectives + a synthesis prompt for Claude to decide.

Triggered manually when the user hits a bottleneck.

Usage:
    from app.swarms.local_council import LocalCouncil

    council = LocalCouncil()
    result = await council.consult(
        problem="The PlannerAgent is producing circular dependencies in task graphs",
        context={"agent": "PlannerAgent", "error": "..."},
    )
    # result.perspectives["qwen"] → technical code-level analysis
    # result.perspectives["llama"] → logical/systemic analysis
    # result.synthesis_prompt → ready to paste to Claude for final decision
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

from app.llm.local_client import LocalModelClient

logger = logging.getLogger(__name__)

_QWEN_SYSTEM = (
    "You are a senior software engineer specializing in Python backend systems, "
    "multi-agent architectures, and debugging complex technical issues. "
    "Analyze the problem from a code-level, implementation perspective. "
    "Be precise, technical, and actionable."
)

_LLAMA_SYSTEM = (
    "You are a systems architect with deep experience in AI pipelines, "
    "distributed systems, and software design patterns. "
    "Analyze the problem from a logical and architectural perspective. "
    "Focus on root causes, trade-offs, and alternative approaches."
)

_USER_TEMPLATE = """\
Problem:
{problem}

Context:
{context}

Provide your analysis:
1. Root cause (what is actually wrong)
2. Proposed solution (specific and actionable)
3. Risks or trade-offs of your solution
4. Alternative approach if your solution fails
"""


@dataclass
class CouncilResult:
    problem: str
    perspectives: dict[str, str] = field(default_factory=dict)  # model → analysis
    elapsed_sec: float = 0.0
    synthesis_prompt: str = ""

    def format(self) -> str:
        """Human-readable output for display."""
        lines = [f"# Second Opinion — Council Results\n", f"**Problem:** {self.problem}\n"]
        for model, analysis in self.perspectives.items():
            lines.append(f"---\n## {model}\n{analysis}\n")
        lines.append(f"---\n## Synthesis prompt (paste to Claude)\n{self.synthesis_prompt}")
        return "\n".join(lines)


class LocalCouncil:
    """Runs two local models in parallel for second opinions."""

    def __init__(self):
        self._qwen = LocalModelClient("qwen2.5-coder:7b")
        self._llama = LocalModelClient("llama3.1:8b")

    async def consult(self, problem: str, context: dict | str = "") -> CouncilResult:
        """Query both local models in parallel and return their perspectives."""
        ctx_str = context if isinstance(context, str) else str(context)
        user_msg = _USER_TEMPLATE.format(problem=problem, context=ctx_str)

        qwen_messages = [
            {"role": "system", "content": _QWEN_SYSTEM},
            {"role": "user", "content": user_msg},
        ]
        llama_messages = [
            {"role": "system", "content": _LLAMA_SYSTEM},
            {"role": "user", "content": user_msg},
        ]

        logger.info("LocalCouncil: consulting qwen2.5-coder + llama3.1 in parallel")
        start = time.monotonic()

        qwen_task = asyncio.create_task(
            self._qwen.chat(qwen_messages, temperature=0.2, max_tokens=1024, agent_name="LocalCouncil")
        )
        llama_task = asyncio.create_task(
            self._llama.chat(llama_messages, temperature=0.3, max_tokens=1024, agent_name="LocalCouncil")
        )

        results = await asyncio.gather(qwen_task, llama_task, return_exceptions=True)
        elapsed = time.monotonic() - start

        perspectives = {}
        for name, res in zip(["qwen2.5-coder:7b", "llama3.1:8b"], results):
            if isinstance(res, Exception):
                logger.warning("Council model %s failed: %s", name, res)
                perspectives[name] = f"[ERROR: {res}]"
            else:
                perspectives[name] = res.text

        synthesis_prompt = _build_synthesis_prompt(problem, perspectives)

        return CouncilResult(
            problem=problem,
            perspectives=perspectives,
            elapsed_sec=round(elapsed, 2),
            synthesis_prompt=synthesis_prompt,
        )


def _build_synthesis_prompt(problem: str, perspectives: dict[str, str]) -> str:
    parts = [
        f"I have a bottleneck and consulted two local models. Here are their analyses:\n",
        f"**Problem:** {problem}\n",
    ]
    for model, analysis in perspectives.items():
        parts.append(f"**{model}:**\n{analysis}\n")
    parts.append(
        "Based on both perspectives, what is the best solution? "
        "Consider technical correctness (qwen) and architectural soundness (llama). "
        "Give me a final decision with implementation steps."
    )
    return "\n".join(parts)


# Module-level singleton
_council: LocalCouncil | None = None


def get_council() -> LocalCouncil:
    global _council
    if _council is None:
        _council = LocalCouncil()
    return _council
