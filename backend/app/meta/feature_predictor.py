"""Feature Predictor — analyzes codebase patterns to predict needed features/fixes.

Reads: git history, error rates from RegressiveMemory, dead letters, BRIEFING.md
Produces: prioritized BacklogItem list
"""

import asyncio
import logging
import subprocess
from typing import Any

from app.meta.pipeline import get_pipeline
from app.meta.schemas import PipelinePhase, BacklogItem

logger = logging.getLogger(__name__)


class FeaturePredictor:
    """Predicts what features, fixes, or improvements the project needs next."""

    def __init__(self, project_dir: str = "."):
        self.project_dir = project_dir

    async def predict(
        self,
        git_log_lines: int = 20,
        include_errors: bool = True,
        max_items: int = 5,
    ) -> list[BacklogItem]:
        """Analyze project state and predict next backlog items."""

        context = await self._gather_context(git_log_lines, include_errors)
        prompt = self._build_prompt(context, max_items)

        pipeline = get_pipeline()
        result = await pipeline.run_single(prompt, PipelinePhase.PREDICT, 2048)

        return self._parse_backlog(result.output, max_items)

    async def _gather_context(self, git_lines: int, include_errors: bool) -> dict:
        """Gather project context from multiple sources."""
        context: dict[str, Any] = {}

        # Git log
        context["git_log"] = await self._get_git_log(git_lines)

        # Error patterns from regressive memory
        if include_errors:
            context["error_patterns"] = await self._get_error_patterns()

        # BRIEFING.md if exists
        context["briefing"] = self._read_file("BRIEFING.md", 1500)

        # Recent spec status
        context["specs"] = self._read_file(".kiro/memory/active_workstream.md", 500)

        return context

    async def _get_git_log(self, lines: int) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "log", f"--oneline", f"-{lines}", "--no-decorate",
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return stdout.decode("utf-8", errors="replace").strip()
        except Exception as e:
            logger.warning("Failed to get git log: %s", e)
            return ""

    async def _get_error_patterns(self) -> str:
        try:
            from app.memory.regressive import RegressiveMemory
            rm = RegressiveMemory()
            # Get failure patterns for a few key agents
            patterns = []
            for agent in ["ClassifierAgent", "ExtractorAgent", "PlannerAgent"]:
                correlations = await rm.get_failure_correlations(agent, "7d")
                if correlations.get("top_failure_conditions"):
                    for cond in correlations["top_failure_conditions"][:2]:
                        patterns.append(f"{agent}: {cond['dimension']}={cond['value']} failure_rate={cond['failure_rate']}")
            return "\n".join(patterns) if patterns else "No significant error patterns detected"
        except Exception as e:
            logger.debug("Error patterns unavailable: %s", e)
            return "Error analysis unavailable (MongoDB not connected)"

    def _read_file(self, path: str, max_chars: int) -> str:
        import os
        full_path = os.path.join(self.project_dir, path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()[:max_chars]
        except (FileNotFoundError, OSError):
            return ""

    def _build_prompt(self, context: dict, max_items: int) -> str:
        parts = [
            f"Analyze this project and predict the top {max_items} features, "
            f"fixes, or improvements needed next.\n\n",
        ]

        if context.get("git_log"):
            parts.append(f"## Recent Git History\n```\n{context['git_log']}\n```\n\n")

        if context.get("error_patterns"):
            parts.append(f"## Error Patterns (last 7 days)\n{context['error_patterns']}\n\n")

        if context.get("briefing"):
            parts.append(f"## Project Briefing\n{context['briefing'][:800]}\n\n")

        if context.get("specs"):
            parts.append(f"## Active Work\n{context['specs']}\n\n")

        parts.append(
            f"## Output Format\n"
            f"For each of the {max_items} items, output:\n"
            f"ITEM: <title>\n"
            f"CATEGORY: feature|bugfix|refactor|performance|security\n"
            f"PRIORITY: critical|high|medium|low\n"
            f"EFFORT: small|medium|large\n"
            f"RATIONALE: <why this is needed>\n"
            f"FILES: <comma-separated affected files>\n"
            f"AGENTS: <comma-separated agent names to use>\n"
            f"---\n"
        )
        return "\n".join(parts)

    def _parse_backlog(self, output: str, max_items: int) -> list[BacklogItem]:
        """Parse LLM output into BacklogItem list."""
        items = []
        current: dict[str, str] = {}

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("ITEM:"):
                if current.get("title"):
                    items.append(self._make_item(current))
                current = {"title": line[5:].strip()}
            elif line.startswith("CATEGORY:"):
                current["category"] = line[9:].strip().lower()
            elif line.startswith("PRIORITY:"):
                current["priority"] = line[9:].strip().lower()
            elif line.startswith("EFFORT:"):
                current["effort"] = line[7:].strip().lower()
            elif line.startswith("RATIONALE:"):
                current["rationale"] = line[10:].strip()
            elif line.startswith("FILES:"):
                current["files"] = line[6:].strip()
            elif line.startswith("AGENTS:"):
                current["agents"] = line[7:].strip()
            elif line == "---":
                if current.get("title"):
                    items.append(self._make_item(current))
                    current = {}

        # Don't forget the last item
        if current.get("title"):
            items.append(self._make_item(current))

        return items[:max_items]

    def _make_item(self, data: dict) -> BacklogItem:
        return BacklogItem(
            title=data.get("title", "Untitled"),
            description=data.get("rationale", ""),
            category=data.get("category", "feature"),
            priority=data.get("priority", "medium"),
            estimated_effort=data.get("effort", "medium"),
            rationale=data.get("rationale", ""),
            affected_files=[f.strip() for f in data.get("files", "").split(",") if f.strip()],
            suggested_agents=[a.strip() for a in data.get("agents", "").split(",") if a.strip()],
        )
