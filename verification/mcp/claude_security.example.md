# Claude Code session — security review

This document is the recipe for the **Claude security review** node
of the triangulation. Run it in a fresh Claude Code session in your
Ubuntu IDE.

## Pre-requisites

- `claude` CLI installed and logged in (Anthropic API key OR
  Claude Pro / Max subscription)
- This repo open as the working directory
- Docker daemon running

## Recommended session prompt

Open Claude Code from this repo and paste:

```
You are the "Claude Security Review" node of a 3-source triangulation
of NexusForge AI. The goal is to produce a security-focused
verification report that another node (AIOS) and another model (GPT-5.5)
will be cross-referenced against.

Scope:
1. Run the verification harness end-to-end:
   - bash verification/bootstrap.sh claude_security
   - capture the printed run_id
   - bash verification/security_scan.sh claude_security <run_id>
   - bash verification/functionality_smoke.sh claude_security <run_id>

2. After the automated layer finishes, do a model-driven review of
   the codebase WITH the security_findings.json + functionality_findings.json
   already on disk. Add findings the automated layer missed:
   - Authorization edge cases (multi-tenant boundary, admin-only routes,
     X-Mythos-Key derivation)
   - Cryptographic agility (Fernet rotation overlap, JWT signing
     algorithm pinning)
   - Prompt injection surface across LLM-fed inputs
   - Session/refresh token handling
   - Race conditions in workflow execution + healing
   - Information leakage via error responses

3. Write `verification/reports/claude_security/<run_id>/report.md`
   following verification/templates/report.template.md. Tag your
   manual findings with [security] / [functionality] etc.

4. DO NOT push commits, DO NOT modify production config, DO NOT
   touch .env (the prod one). Use only .env.verify.

5. When done, print a one-line summary like:
   "claude_security run <run_id>: <N> automated findings + <M> manual findings"
```

## Optional: enable `/security-review` skill

If you have the security-review skill installed:

```
/security-review verification/reports/claude_security/<run_id>/security_findings.json
```

…and append its output to `report.md` under "Recommendations".

## Cleanup

Don't tear down the verify stack inside this session — leave it up
so the triangulator can rerun if needed. The next session
(AIOS or GPT-5.5) can reuse the same stack via `--skip-bootstrap`
(see future enhancement; for now, each session brings up its own).
