"""Architecture Reasoner — uses thinking mode to reason about design decisions.

Input: feature description + codebase context
Output: ArchitectureDecision with structured reasoning, trade-offs, file impact
"""

import logging
from app.meta.pipeline import get_pipeline
from app.meta.schemas import (
    PipelinePhase, ArchitectureDecision,
)

logger = logging.getLogger(__name__)


class ArchitectureReasoner:
    """Reasons about architecture decisions before implementation."""

    async def reason(
        self,
        feature_description: str,
        codebase_context: str = "",
        existing_architecture: str = "",
    ) -> ArchitectureDecision:
        """Analyze a feature and produce a structured architecture decision.

        Uses THINK phase (gemma with thinking mode) for deep reasoning.
        """
        prompt = self._build_prompt(feature_description, codebase_context, existing_architecture)

        pipeline = get_pipeline()
        result = await pipeline.run_single(
            prompt=prompt,
            phase=PipelinePhase.THINK,
            max_tokens=3000,
        )

        return self._parse_response(result.output, result.thinking)

    def _build_prompt(self, feature: str, context: str, architecture: str) -> str:
        parts = [
            "Analyze this feature request and produce an architecture decision.\n",
            f"## Feature Request\n{feature}\n",
        ]
        if context:
            parts.append(f"## Codebase Context\n{context[:2000]}\n")
        if architecture:
            parts.append(f"## Current Architecture\n{architecture[:2000]}\n")

        parts.append(
            "## Required Output Format\n"
            "Respond with these sections:\n"
            "### Summary\nOne paragraph summary of the decision.\n"
            "### Trade-offs\nList pros and cons as bullet points.\n"
            "### Affected Files\nList files that need changes.\n"
            "### Dependencies\nList external dependencies or services impacted.\n"
            "### Risk Assessment\nWhat could go wrong.\n"
            "### Recommendation\nClear recommendation on how to proceed.\n"
        )
        return "\n".join(parts)

    def _parse_response(self, output: str, thinking: str) -> ArchitectureDecision:
        """Parse LLM output into structured ArchitectureDecision."""
        sections = _split_sections(output)

        trade_offs = []
        if "trade-offs" in sections:
            for line in sections["trade-offs"].splitlines():
                line = line.strip().lstrip("-•* ")
                if not line:
                    continue
                if "pro" in line.lower() or "+" in line[:3]:
                    trade_offs.append({"pro": line, "con": ""})
                elif "con" in line.lower() or "-" in line[:3]:
                    if trade_offs:
                        trade_offs[-1]["con"] = line
                    else:
                        trade_offs.append({"pro": "", "con": line})
                else:
                    trade_offs.append({"pro": line, "con": ""})

        affected = _extract_file_list(sections.get("affected files", ""))
        deps = _extract_file_list(sections.get("dependencies", ""))

        return ArchitectureDecision(
            summary=sections.get("summary", output[:500]),
            thinking_trace=thinking,
            trade_offs=trade_offs,
            affected_files=affected,
            dependencies=deps,
            risk_assessment=sections.get("risk assessment", ""),
            recommendation=sections.get("recommendation", ""),
        )


def _split_sections(text: str) -> dict[str, str]:
    """Split markdown text by ### headers into a dict."""
    sections: dict[str, str] = {}
    current_key = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("###"):
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = line.lstrip("#").strip().lower()
            current_lines = []
        else:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def _extract_file_list(text: str) -> list[str]:
    """Extract file paths from bullet list or backtick-wrapped items."""
    files = []
    for line in text.splitlines():
        line = line.strip().lstrip("-•* ")
        # Extract from backticks
        if "`" in line:
            start = line.index("`") + 1
            end = line.index("`", start) if "`" in line[start:] else len(line)
            files.append(line[start:end])
        elif "/" in line or "." in line:
            files.append(line.split()[0] if line.split() else line)
    return [f for f in files if f]
