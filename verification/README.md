# Triangulation harness

The canonical pass uses **6 independent verification sessions**, each
producing findings in the same JSON shape so the triangulator can
cross-reference them by agreement. None are optional — they're all
mandatory for a full pass:

| # | Tool id | Engine | Focus |
|---|---|---|---|
| 1 | `claude_security` | Claude Code (cloud) | Security analysis with model-driven manual findings |
| 2 | `gpt55` | GPT-5.5 via Codex CLI (cloud) | Correctness / refactoring / API contract |
| 3 | `aios` | AIOS CLI (`pip install aios-kiro-master`) | Persistent-memory cross-ref against historical decisions |
| 4 | `deepseek_local` | DeepSeek-R1 8B via Ollama (host) | Security, CoT-reasoning visible |
| 5 | `qwen_local` | Qwen 3 8B via Ollama (host) | Technical / code-quality |
| 6 | `llama_local` | Llama 3.1 8B via Ollama (host) | Functional / UX / docs |

Each cloud node bootstraps its own isolated stack via
`docker-compose.verify.yml` (project name `nexusforge_verify`, ports
shifted to avoid dev collisions). The AIOS and local-LLM nodes layer
ON TOP of the existing run output (`security_findings.json` +
`functionality_findings.json`) so they don't need their own bootstrap
— they pick up findings from any prior tool's run.

A separate triangulator merges all six and surfaces issues by
**agreement**: 6/6 sources flagging the same thing is essentially
certain; 1/6 is a single-source claim that warrants investigation but
isn't load-bearing on its own.

## Why three sessions

A single LLM session has blind spots that are correlated with its
training data and tool selection. Three different model families
(or the same model with different toolchains) have *different*
blind spots — so an issue that all three flag is much less likely
to be a hallucination, and an issue only one flags can be
de-prioritized as a false-positive candidate.

## Tool ids (used as report subdirs)

See the table at the top of this README. Each tool writes into
`verification/reports/<tool_id>/<run_id>/`.

## What each session runs

The cloud nodes (claude_security, gpt55) run the full harness; the
AIOS and local-LLM nodes layer evaluations on top of the existing
findings without bootstrapping their own stack.

```bash
# Step 1 — bootstrap the verify stack and tools
bash verification/bootstrap.sh <tool_id>
# Reads .env.verify (created from env.verify.example with auto-generated
# secrets if absent). Brings up docker-compose.verify.yml on isolated
# ports. Installs gitleaks/semgrep/pip-audit/schemathesis if missing.
# Persists run_metadata.json under verification/reports/<tool>/<run_id>/.

# Step 2 — security scan
bash verification/security_scan.sh <tool_id> <run_id>
# Hits Mythos via the live backend, runs pip-audit/npm-audit/gitleaks/
# semgrep/schemathesis. Normalizes everything into security_findings.json.

# Step 3 — functionality smoke
bash verification/functionality_smoke.sh <tool_id> <run_id>
# Runs the canonical golden-path harness against the live stack.
# Writes functionality_findings.json (failures = findings).

# Step 4 — analyst-authored markdown
# Each session ALSO writes a freeform report.md following
# verification/templates/report.template.md so the model's qualitative
# judgments (architecture concerns, gaps the automated layer can't see)
# are captured. Save it as:
#   verification/reports/<tool_id>/<run_id>/report.md
```

After all three sessions finish:

```bash
python3 verification/triangulate.py
# Merges findings across the most-recent run from each tool, emits:
#   verification/reports/_triangulation/<run_ts>/triangulation.{json,md}
```

## Running the same machine, multiple sessions

The user's setup: one Ubuntu machine, three IDE windows / sessions
sharing the same docker host. The verify stack uses a project name
(`nexusforge_verify`) and isolated ports (18000/15173/15432/16379/
27018/11435), so it doesn't collide with the dev `docker-compose.yml`.

Two strategies:

1. **Sequential (recommended for first pass)**: each session brings
   up the stack, runs both scans, tears down, then the next session
   starts. Total time ~3× single run.
2. **Shared stack (faster, but sessions share state)**: one session
   bootstraps once, all three run their scans against it. Note: the
   smoke harness creates test users, so each session must use a
   different `tool_id` to avoid collisions on the test_email seed.
   Tear down with `docker compose -f docker-compose.verify.yml -p nexusforge_verify down -v`.

## Tool-specific MCP / connector wireup

See `verification/mcp/`:

- `aios.example.md` — AIOS install + CLI invocation reference (NOT MCP — `aios` is a CLI tool, not an MCP server; install via `pip install aios-kiro-master`)
- `claude_security.example.md` — how to launch a Claude Code session
  with the right skills + working directory
- `codex.example.md` — Codex CLI invocation for the GPT-5.5 session

Each session must have its own credential set (Anthropic key for
Claude, OpenAI key for Codex/GPT, AIOS key for AIOS). NEVER share
prod keys — the verify environment uses test secrets only.

## What goes in the per-session report

The automated layer captures `findings.json` files (security +
functionality). The model session also writes a markdown report
(`report.md`) using `verification/templates/report.template.md`,
where the analyst surfaces things the harness can't see:

- Architecture concerns
- UX gaps in the dashboards
- Performance smells
- Documentation drift between code and CLAUDE.md / docs
- Roadmap risks

Tag manual findings inside `report.md` with `[security]` /
`[functionality]` / `[ux]` / `[performance]` / `[ops]` so they can
be picked up by future tooling.

## Failure modes (and what they mean)

| Symptom | Likely cause | Fix |
|---|---|---|
| `bootstrap.sh` hangs at "waiting for backend healthy" | DB not ready (slow disk) or env-var typo | `docker compose -f docker-compose.verify.yml logs backend` — look for migration or env errors |
| Mythos scan returns `{"error":"endpoint unavailable"}` | Backend `MYTHOS_HMAC_SECRET` doesn't match what bootstrap.sh derived the key from | Regenerate `.env.verify`, restart stack |
| schemathesis fails on every endpoint | Backend OpenAPI not exposing schemas | Verify `/api/openapi.json` returns 200; some routers may need `tags=` |
| Functionality smoke reports `auth` failed → cascade of `skipped: no auth token` | Register endpoint expects different shape (e.g., `username` not `email`) | Adjust `_smoke_harness.smoke_auth` payload to match current API |

## Cleanup

After a triangulation pass:

```bash
# Tear down the verify stack and its volumes (keeps your dev stack alone)
docker compose -f docker-compose.verify.yml -p nexusforge_verify down -v
# Remove all verify-tagged volumes (handles orphans from prior runs)
docker volume prune --filter label=verify-only --force
# Wipe synthesizer scratch dir
rm -rf /tmp/nexusforge_verify_synth
```
