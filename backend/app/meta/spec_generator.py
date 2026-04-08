"""Auto-Spec Generator — produces Kiro-compatible spec files automatically.

Pipeline: THINK (requirements analysis) → BUILD (structured spec generation)
Optionally: → VERIFY (validate spec completeness)

Output: KiroSpec with requirements.md, design.md, tasks.md
"""

import logging
import os
from pathlib import Path

from app.meta.pipeline import get_pipeline
from app.meta.schemas import (
    PipelinePhase, KiroSpec, ArchitectureDecision, SpecGenerationRequest,
)

logger = logging.getLogger(__name__)


class SpecGenerator:
    """Generates Kiro-compatible spec files from feature descriptions."""

    async def generate(
        self,
        feature_description: str,
        spec_type: str = "feature",
        architecture_decision: ArchitectureDecision | None = None,
        codebase_context: str = "",
        verify: bool = True,
    ) -> KiroSpec:
        """Generate a complete Kiro spec (3 files).

        Args:
            feature_description: What needs to be built/fixed
            spec_type: feature, bugfix, refactor, migration
            architecture_decision: Optional pre-computed architecture analysis
            codebase_context: BRIEFING.md or similar context
            verify: Whether to run VERIFY phase on generated spec
        """
        pipeline = get_pipeline()

        # Phase 1: THINK — analyze requirements
        think_prompt = self._build_think_prompt(
            feature_description, spec_type, architecture_decision, codebase_context
        )
        think_result = await pipeline.run_single(think_prompt, PipelinePhase.THINK, 2048)

        # Phase 2: BUILD — generate the 3 spec files
        build_prompt = self._build_spec_prompt(
            feature_description, spec_type, think_result.output, architecture_decision
        )
        build_result = await pipeline.run_single(build_prompt, PipelinePhase.BUILD, 4096)

        spec = self._parse_spec(feature_description, build_result.output)

        # Phase 3: VERIFY (optional) — validate completeness
        if verify:
            verify_prompt = self._build_verify_prompt(spec, feature_description)
            verify_result = await pipeline.run_single(verify_prompt, PipelinePhase.VERIFY, 2048)

            # If verifier found issues, note them in the spec
            if "issue" in verify_result.output.lower() or "missing" in verify_result.output.lower():
                spec.tasks_md += f"\n\n## Verification Notes\n{verify_result.output[:500]}"

        return spec

    def write_to_disk(self, spec: KiroSpec, base_dir: str) -> str:
        """Write spec files to .kiro/specs/{slug}/ directory."""
        spec_dir = os.path.join(base_dir, ".kiro", "specs", spec.slug)
        os.makedirs(spec_dir, exist_ok=True)

        for filename, content in [
            ("requirements.md", spec.requirements_md),
            ("design.md", spec.design_md),
            ("tasks.md", spec.tasks_md),
        ]:
            path = os.path.join(spec_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        # Config file for Kiro
        config = {
            "specId": spec.slug,
            "workflowType": "requirements-first",
            "specType": "feature" if "feature" in spec.slug else "bugfix",
        }
        import json
        with open(os.path.join(spec_dir, ".config.kiro"), "w") as f:
            json.dump(config, f, indent=2)

        logger.info("Spec written to %s", spec_dir)
        return spec_dir

    def _build_think_prompt(
        self, feature: str, spec_type: str,
        arch: ArchitectureDecision | None, context: str,
    ) -> str:
        parts = [
            f"Analyze this {spec_type} request and identify requirements:\n",
            f"## Request\n{feature}\n",
        ]
        if arch:
            parts.append(f"## Architecture Decision\n{arch.summary}\n{arch.recommendation}\n")
        if context:
            parts.append(f"## Project Context\n{context[:1500]}\n")
        parts.append(
            "Identify:\n"
            "1. Functional requirements (what must work)\n"
            "2. Non-functional requirements (performance, security)\n"
            "3. Preservation requirements (what must NOT break)\n"
            "4. Affected components and files\n"
            "5. Testing strategy\n"
        )
        return "\n".join(parts)

    def _build_spec_prompt(
        self, feature: str, spec_type: str,
        analysis: str, arch: ArchitectureDecision | None,
    ) -> str:
        template = _get_template(spec_type)

        return (
            f"Generate a Kiro-compatible spec for this {spec_type}.\n\n"
            f"## Feature\n{feature}\n\n"
            f"## Analysis\n{analysis}\n\n"
            f"{'## Architecture' + chr(10) + arch.summary + chr(10) + chr(10) if arch else ''}"
            f"## Output Format\n"
            f"Generate THREE markdown documents separated by `---SPLIT---`:\n\n"
            f"DOCUMENT 1: requirements.md\n{template['requirements']}\n\n"
            f"DOCUMENT 2: design.md\n{template['design']}\n\n"
            f"DOCUMENT 3: tasks.md\n{template['tasks']}\n\n"
            f"Use `---SPLIT---` between each document. Start now."
        )

    def _build_verify_prompt(self, spec: KiroSpec, feature: str) -> str:
        return (
            f"Verify this spec is complete and correct.\n\n"
            f"## Original Request\n{feature}\n\n"
            f"## Requirements\n{spec.requirements_md[:1000]}\n\n"
            f"## Tasks\n{spec.tasks_md[:1000]}\n\n"
            f"Check:\n"
            f"1. Every requirement has at least one task\n"
            f"2. No orphan tasks (tasks without a requirement)\n"
            f"3. Task order is logical (dependencies respected)\n"
            f"4. Testing tasks are included\n"
            f"5. Preservation/regression tasks are included\n"
            f"Report issues found or say 'Spec is complete'."
        )

    def _parse_spec(self, feature: str, output: str) -> KiroSpec:
        """Parse the BUILD phase output into a KiroSpec."""
        parts = output.split("---SPLIT---")

        requirements = parts[0].strip() if len(parts) > 0 else f"# Requirements: {feature}\n\n(Generation failed)"
        design = parts[1].strip() if len(parts) > 1 else f"# Design: {feature}\n\n(Generation failed)"
        tasks = parts[2].strip() if len(parts) > 2 else f"# Tasks: {feature}\n\n- [ ] Implement feature"

        return KiroSpec(
            feature_name=feature[:80],
            requirements_md=requirements,
            design_md=design,
            tasks_md=tasks,
        )


def _get_template(spec_type: str) -> dict[str, str]:
    """Return template structure for each spec type."""
    if spec_type == "bugfix":
        return {
            "requirements": "# Bugfix Requirements\n## Bug Description\n## Expected Behavior\n## Preservation Requirements",
            "design": "# Bugfix Design\n## Root Cause Analysis\n## Fix Approach\n## Correctness Properties",
            "tasks": "# Tasks\n- [ ] Write reproduction test\n- [ ] Implement fix\n- [ ] Verify test passes\n- [ ] Run full suite",
        }
    elif spec_type == "refactor":
        return {
            "requirements": "# Refactor Requirements\n## What to Refactor\n## Why\n## Constraints",
            "design": "# Refactor Design\n## Current State\n## Target State\n## Migration Steps",
            "tasks": "# Tasks\n- [ ] Write characterization tests\n- [ ] Implement refactor\n- [ ] Verify tests pass",
        }
    else:  # feature (default)
        return {
            "requirements": "# Feature Requirements\n## Problem\n## Requirements (numbered)\n## Non-functional Requirements",
            "design": "# Feature Design\n## Architecture\n## Data Model\n## API Changes\n## UI Changes",
            "tasks": "# Tasks\n## Phase 1\n- [ ] Task 1\n## Phase 2\n- [ ] Task 2\n## Verification\n- [ ] End-to-end test",
        }
