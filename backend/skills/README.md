# NexusForge Skills

Filesystem-based skills for NexusForge agents. Follows the Anthropic Agent Skills
specification: each skill lives in its own directory with a `SKILL.md` file that
has YAML frontmatter (`name`, `description`) and a markdown body with the
instructions.

## Why skills (vs. hardcoded prompts in Python)

- **Lazy loading**: Claude loads only the skill *name* into context at start,
  pulling in the full body only when the skill is actually needed. This avoids
  bloating the context window with 24 agent prompts upfront.
- **Editable without code changes**: rewording a classifier prompt no longer
  requires a Python edit + redeploy.
- **Reusable across runtimes**: the same SKILL.md can be loaded into the
  Agent SDK, Claude API with `container`, or the local Ollama path as a
  plain system prompt.

## Structure

```
backend/skills/
  classifier/
    SKILL.md            # classifier prompt + metadata
  qwen-coder/
    SKILL.md            # code-generation system prompt
  csharp-analyzer/
    SKILL.md            # C# static analysis prompt
  pii-scanner/
    SKILL.md            # PII detection prompt
```

## SKILL.md format

```markdown
---
name: classifier
description: Classify documents into legal, financial, technical, medical, or general categories.
---

# Body — full instructions used as the system prompt when the skill is loaded.
```

## Status

This directory is in its initial bootstrap. Only `classifier/` has been ported
as a reference. The remaining 23 agents will be migrated in Feature 2 (Agent
Skills integration) per the 4-feature Anthropic adoption plan.

Runtime loader is **not yet wired** — this directory is currently static
documentation. See `backend/app/agents/skill_loader.py` (TBD) for the parser.
