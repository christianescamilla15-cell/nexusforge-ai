# Codex CLI session — GPT-5.5 verification node

This document is the recipe for the **GPT-5.5** node of the
triangulation. Run it in a fresh Codex CLI session in your Ubuntu IDE.

## Pre-requisites

- `codex` CLI installed (`pip install codex` or via the OpenAI installer)
- `OPENAI_API_KEY` env var set (use a key with GPT-5.5 access)
- This repo open as the working directory
- Docker daemon running

## Codex MCP wireup (optional but recommended)

Codex's recent versions speak MCP. To give the GPT-5.5 session
access to AIOS's tools (so you can cross-reference into AIOS memory
inline), drop into `~/.codex/mcp.json`:

```json
{
  "mcpServers": {
    "aios": {
      "command": "aios",
      "args": ["mcp", "serve"],
      "env": {
        "AIOS_PROJECT_ROOT": "/home/danny/Desktop/portafolio-completo/proyectos/07-nexusforge-ai"
      }
    }
  }
}
```

If Codex on your version doesn't have native MCP support, skip this
— the harness scripts work without it.

## Recommended session prompt

Launch `codex` in the repo and paste:

```
You are the "GPT-5.5" node of a 3-source triangulation of NexusForge AI.
Two other nodes (AIOS plugin + Claude Code with security-review)
are doing the same work in parallel sessions. The triangulator
script will cross-reference all three for agreement.

Your job:

1. Run the verification harness end-to-end (use bash via the shell tool):
   bash verification/bootstrap.sh gpt55
   bash verification/security_scan.sh gpt55 <run_id_from_step_1>
   bash verification/functionality_smoke.sh gpt55 <run_id>

2. Read the resulting JSON files:
   verification/reports/gpt55/<run_id>/security_findings.json
   verification/reports/gpt55/<run_id>/functionality_findings.json

3. Add a model-driven review on top, focusing on areas the automated
   scanners are weak at:
   - End-to-end correctness across the platform-synth chat → build flow
   - Refactor engine: do the C# fixes actually parse + retain semantics?
   - Multi-agent orchestration: are the 24-agent fallback chains sound?
   - Performance: any obvious N+1 / unnecessary roundtrips?
   - Documentation accuracy: do the API endpoints in CLAUDE.md still match main.py?

4. Write `verification/reports/gpt55/<run_id>/report.md` following
   verification/templates/report.template.md. Tag manual findings.

5. CONSTRAINTS:
   - Use only .env.verify (NEVER .env)
   - No git pushes
   - No prod config changes
   - The verify stack uses dedicated ports (18000 backend, 15173
     frontend) — don't try to use the dev ones (8000/5173)

6. Print a one-line summary on completion:
   "gpt55 run <run_id>: <N> automated findings + <M> manual findings"
```

## Why GPT-5.5 specifically

Different model family from Claude → different blind spots. GPT
historically catches more correctness/refactoring issues, while
Claude tends to be stronger at security reasoning. Their disagreements
in the triangulation are interesting signal — both flagging the same
thing means it's almost certainly real.

## Cleanup

Same as the Claude session — leave the verify stack up until the
triangulator runs. Final cleanup:

```bash
docker compose -f docker-compose.verify.yml -p nexusforge_verify down -v
```
