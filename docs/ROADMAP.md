# NexusForge Roadmap (consolidated)

> **Single source of truth for "what's next".** This document is an
> index — it points to the detailed docs that hold the real design
> decisions, and it tracks the status of all active workstreams in one
> place. When status in a detailed doc conflicts with this file, update
> this file to match and leave the detailed doc as the archived source
> of that decision.
>
> **Last updated:** 2026-04-10
> **Maintainer:** Christian Hernandez (sole owner)

## 1. Current state snapshot

### Live URLs
- **Frontend:** https://nexusforge-two.vercel.app (manual deploy via `vercel --prod`)
- **Backend API:** https://nexusforge-api.onrender.com/api (auto-deploys from `master`)
- **Portfolio:** https://ch65-portfolio.vercel.app
- **Repo:** PRIVATE at `christianescamilla15-cell/nexusforge-ai`

### Scale (confirmed via CLAUDE.md + codebase read on 2026-04-10)
- **Backend:** Python 3.12 + FastAPI, ~95 endpoints, ~307 unit tests + 17 functional
- **Frontend:** React 18 + Vite 8, 16 URL-routed pages, 40+ custom components
- **DB:** PostgreSQL 16 + pgvector, 25+ tables, 9+ migrations (runner present + hardened in `97f1112`)
- **24 agents** in `backend/app/agents/` with per-agent model routing
- **5-tier memory:** working → episodic (Redis+Mongo) → semantic (pgvector) → regressive → predictive
- **LLM fallback chain:** Ollama → Haiku → Groq → Claude (with prompt caching)

### What is live in production
- DAG workflow execution, 6 swarm topologies, self-healing (5 strategies)
- Multi-tenant SaaS foundation with RLS (Row-Level Security)
- Stripe metered billing, API key scopes, HMAC webhooks, Sentry error tracking
- **Mythos** security auditor (9 scan categories, owner-only via HMAC-SHA512)
- **Refactoring Engine** with 15 modules: ingestion, C# analyzer/fixer, PII scanner,
  DB analyzer, test generator, CI/CD generator, RPA scanner, multi-repo,
  triage, batch pipeline, rollback, PR generator, engine
- **Tenant-alpha showcase** dashboard (publicly visible under `/showcase`)
- Executive C-level dashboard (`/executive`)
- Chat-first UX with WebSocket execution tracking

### What is in feature branches pending merge (as of 2026-04-10)
- `feature/anthropic-sdk-bump` (commit `7514157`) — `anthropic==0.34.0 → 0.94.0`
- `feature/context-editing` (commits `04cf05d` + `e7555bb`) — Feature 1 of the
  Anthropic 4-feature adoption: provider chain plumbing + batch pipeline wiring
  with 25 new tests (all green)

### What is in research/planning (no code yet)
- **Anthropic 4-feature adoption Phases 3–6** — see
  [`anthropic-features-research.md`](./anthropic-features-research.md) §12
- **Gaps 6, 8, 9, 10, 12** of the "Platform of the Future" vision — see §3
  below

---

## 2. Active workstreams

There are **4 parallel workstreams** right now. Each has a canonical
detail document; this file only surfaces status.

| # | Workstream | Canonical doc | Status |
|---|---|---|---|
| 1 | **Tenant-alpha showcase** — the synthetic-codebase demo of NexusForge modernizing 5 (then 31) legacy apps in "weeks not years" | [`integration/01_agent_mapping.md`](./integration/01_agent_mapping.md), [`integration/02_phase2_plan.md`](./integration/02_phase2_plan.md), [`integration/03_future_platform_vision.md`](./integration/03_future_platform_vision.md) | Phase A (5 apps, 900K LOC) **shipped**; Phase B scale (31 apps, 5.6M LOC) **pending** |
| 2 | **Platform of the Future — 12 capability gaps** driving the showcase narrative | [`integration/03_future_platform_vision.md`](./integration/03_future_platform_vision.md) §Gaps | **7 of 12 shipped** (1, 2, 3, 4, 5, 7, 11); 5 pending (6, 8, 9, 10, 12) |
| 3 | **Anthropic 4-feature adoption** — Context Editing, Memory Tool, Skills, Agent SDK subagents | [`anthropic-features-research.md`](./anthropic-features-research.md) §12, §12.1 | **Phases 0-2 done** (quick wins shipped + Feature 1 on feature branches); Phases 3-6 pending |
| 4 | **Orchestrator improvements** — Claude Code customizations for this project (not part of NexusForge the product) | Local to `.claude/` + memory (gitignored) | 3 subagents + 2 skills + 2 hooks + 2 feedback memories **active**; Render/GitHub/Postgres MCPs **waiting for API keys** |

---

## 3. Gap closure status — 12 capability gaps

From [`integration/03_future_platform_vision.md`](./integration/03_future_platform_vision.md)
§Implications. Each gap is a capability NexusForge must have to be credible
as "Platform of the Future" for enterprise modernization.

| # | Capability | Phase | Status | Evidence |
|---|---|---|---|---|
| 1 | Multi-language SQLi detection (Python/PHP/Java) | 3 | ✅ SHIPPED | `b176878 feat(refactor): Phase 3 — multi-language vulnerability scanner (Gap 1)` |
| 2 | COBOL scanner + FastAPI wrapper-generator | 4 | ✅ SHIPPED | `709d8d8 feat(refactor): COBOL scanner + FastAPI wrapper generator (Gap 2)` |
| 3 | Strangler-pattern migration planner | 4 | ✅ SHIPPED | `233660c feat(refactor): Phase 4 — strangler-pattern migration planner (Gap 3)` |
| 4 | IaC generator (Terraform + Helm + kustomize) | 5 | ✅ SHIPPED | `846a431 feat(refactor): IaC generator (Terraform + Helm + kustomize) — Gap 4` |
| 5 | GitFlow + pipeline governance template | 5 | ✅ SHIPPED | `8c6a367 feat(refactor): GitFlow governance template generator (Gap 5)` |
| 6 | **Data pipeline modernization planner** (flat-file batch → Kafka/Kinesis/MSK recommendation + schema inference) | 5 | ❌ PENDING | — |
| 7 | Compliance-by-design enforcer (template security middleware) | 5 | ✅ SHIPPED | `86bc0ae feat(refactor): compliance-by-design enforcer (middleware templates) — Gap 7` |
| 8 | **AI-powered documentation generator** (runbooks, C4 diagrams, ADRs from refactored code) | 5 | ❌ PENDING | — |
| 9 | **Vendor lock-in escape analyzer** (contract obsolescence audit, portability recommendations) | 6 | ❌ PENDING | — |
| 10 | **Encrypted data pipeline scaffolder** (field-level encryption at source, PII tokenization, data-flow viz) | 6 | ❌ PENDING | — |
| 11 | Observability stack bootstrapper (SLO + cloud-native monitoring + business anomaly alerting) | 6 | ✅ SHIPPED | `d0a86bd feat(refactor): observability stack bootstrapper (Gap 11)` |
| 12 | **Post-modernization knowledge transfer mode** (persistent tech-lead AI agent) | 7 | ❌ PENDING | — |

**Showcase minimum viable scope** per the vision doc: Gaps **1, 2, 3, 5, 7**
must ship to prove "weeks not years". **All 5 are shipped.** The remaining
7 gaps (4 shipped + 3 pending among those not required for MVP) are
expansions for Phase B / 31-app scale / post-MVP polish.

---

## 4. Pending work — categorized by unblocking

### 4.A — Ready now (no external dependencies, can be done in any session)

| Item | Effort | Notes |
|---|---|---|
| Phase B scale: 5 apps → 31 apps in synthetic generator | M (1-2 sessions) | Per `integration/02_phase2_plan.md` — extend per-app recipes, target 5.6M LOC total, hit "real scale" for the demo narrative |
| Gap 6: Data pipeline modernization planner | M (1-2 sessions) | Detect flat-file batch ingestion in legacy code → recommend Kafka/Kinesis/MSK replacement with schema inference |
| Gap 8: AI-powered documentation generator | M (1 session) | Runbooks, C4 diagrams, ADRs auto-generated from refactored code — closes the "no docs" gap in every synthetic app |
| Gap 12: Post-modernization knowledge transfer mode | S/M | Persistent AI agent that stays after delivery to mentor internal team. Leverages existing Agent SDK bridge + memory tiers |
| `backend/scripts/audit_confidentiality.py` — confirm exists + blocklist automation | XS | Per `integration/02_phase2_plan.md` §confidentiality audit; if script exists, verify it blocks real names across the tree and is wired into pre-commit |
| Update `CHANGELOG.md` (root) — stale since v2.5.0 2026-04-04 | S | Capture the 12+ days of work since (Gaps 1-5, 7, 11 shipped, Batch 3 deliverables, mobile fixes, Feature 1 prep) |
| Update `PROJECT_SUMMARY.md` — stale counts ("22 agents", "260 tests") | XS | Refresh to match `CLAUDE.md` |
| Verify P0/P1 items from `IMPLEMENTATION_AUDIT.md` (2026-03-29) — most are likely fixed | S | Cross-check against git log since audit date. Known-fixed: migration runner (`97f1112`), observability bootstrapper (`d0a86bd`), 5-tier memory (`43383f4`). Known-unknown: self-healing wiring into step_runner, state machine enforcement, memory used by agents during execution |

### 4.B — Waiting for API keys (Christian to create)

| Item | Blocker | Effort once unblocked | Value |
|---|---|---|---|
| Render MCP server activation | `RENDER_API_KEY` | XS (paste snippet from `docs/mcp-servers-setup.md` §3) | **HIGH** — eliminates the PUT `/env-vars` critical-rule risk via atomic GET→merge→PATCH primitives |
| GitHub MCP server activation (optional) | `GH_TOKEN` with `repo` scope | XS | Low — the `gh` CLI is already sufficient for most operations |
| Postgres MCP server activation | `DATABASE_URL` (read-only role strongly recommended) | S (includes creating the `claude_readonly` role per the doc's SQL block) | Medium — lets me query the live DB mid-conversation without writing Python scripts |

Recipes already written and tested: see [`mcp-servers-setup.md`](./mcp-servers-setup.md)

### 4.C — Waiting for PR merge

| Branch | Commits | Unblocks |
|---|---|---|
| `feature/anthropic-sdk-bump` | `7514157` | Feature 1 (Context Editing), Feature 3 (Memory Tool) — both need `anthropic>=0.50.0` which is 0.94.0 in this bump |
| `feature/context-editing` (based on bump) | `04cf05d` + `e7555bb` | Feature 1 end-to-end: provider chain plumbing + batch pipeline stub replacement |

**Merge order:** bump first, then context-editing. **Validation before merge:** see `anthropic-features-research.md` §12.1.5 (4-item checklist including `ANTHROPIC_API_KEY` on Render, full pytest, sanity remediation run, merge order).

### 4.D — Research-pending (Anthropic 4-feature adoption Phases 3-6)

From [`anthropic-features-research.md`](./anthropic-features-research.md) §12:

| Phase | Feature | Effort | Prereq |
|---|---|---|---|
| 3 | Feature 3: Memory Tool (ComplianceAgent + PlannerAgent integration) | M/L (12-18h) | SDK bump PR merged |
| 4 | Feature 4: Agent SDK subagent memory + resume | S/M (4-8h) | SDK bump PR merged, Redis for session persistence |
| 5a | Feature 2 (PR 5a): Skills infrastructure (`skill_loader.py`, `_build_system_prompt_v2`) | M (8-12h) | None |
| 5b | Feature 2 (PR 5b): Skills migration — ClassifierAgent, ComplianceAgent, PlannerAgent, 4 Agent SDK subagents, + 19 more | L (20-30h across multiple PRs) | Infrastructure from 5a |
| 6 | Mythos upgrades — second-pass FP filter, diff-aware mode, category-per-skill migration, memory="project" on security-auditor subagent | M (8-12h) | Optional: Features 2 and 4 make it nicer but not blocking |

### 4.E — Long-term / post-MVP gaps (can be deferred past the current demo)

- **Gap 9**: Vendor lock-in escape analyzer — high value for real enterprise sales conversations, not needed for the tenant-alpha showcase
- **Gap 10**: Encrypted data pipeline scaffolder — tied to Phase B compliance story
- Phase B of tenant-alpha showcase (31 apps / 5.6M LOC)
- Integration tests (currently zero per IMPLEMENTATION_AUDIT)
- Frontend dashboard real-data wiring (if not already fixed by later commits — needs verification)

### 4.F — Stale audit items needing verification

[`IMPLEMENTATION_AUDIT.md`](./IMPLEMENTATION_AUDIT.md) is from **2026-03-29** —
~315 commits ago. Many P0/P1 items are probably fixed but not confirmed. A
**5-minute audit refresh pass** would be worth doing before any new work:

- [ ] P0 #1: Self-healing wired into `step_runner.py`? Check `backend/app/engine/step_runner.py` for `SelfHealer.attempt_heal` call
- [ ] P0 #2: Observability unified? Check `backend/app/routes/executions.py` line 52 for `ctx.tracker` passing (likely fixed by `d0a86bd`)
- [ ] P0 #3: Frontend dashboard real data? Check `frontend/src/features/dashboard/DashboardPage.jsx` — was 100% demo in audit
- [ ] P1 #4: Migration runner exists? **Confirmed yes** — `97f1112 fix(migrations): unblock 031 CREATE POLICY + harden runner on failure` implies the runner is present and hardened
- [ ] P1 #5: State machine enforced? Check `engine/executor.py` for `transition_workflow` calls
- [ ] P1 #6: Memory used by agents during execution? Check any agent's `execute()` for `MemoryManager.recall` / `remember` calls
- [ ] P1 #7: Auth middleware enforcing routes? Check `main.py` for `AuthMiddleware` — **confirmed yes** per session read (line 159)

After the verification pass, either retire the audit file (mark as historical,
superseded by this roadmap) or update it in place with "fixed by commit X" tags.

---

## 5. Source documents (authoritative references)

### Tenant-alpha + platform vision (tied to external engagement)

- [`integration/01_agent_mapping.md`](./integration/01_agent_mapping.md) —
  mapping from external 6-agent system to NexusForge's 23 agents + refactor
  modules. Locks in codenames, confidentiality rule, Phase 1 deliverables.
- [`integration/02_phase2_plan.md`](./integration/02_phase2_plan.md) —
  tenant bootstrap + synthetic codebase generator design. Module layout,
  per-app recipes, verification checklist.
- [`integration/03_future_platform_vision.md`](./integration/03_future_platform_vision.md) —
  end-state architecture for real enterprise modernization. 15 sections
  covering target architecture, compliance drivers, ops model, 12 capability
  gaps, Batch 2 + Batch 3 corrections, synthetic generator implications.
  **This is the master vision doc.**

### Anthropic adoption

- [`anthropic-features-research.md`](./anthropic-features-research.md) —
  1,415-line research doc mapping Context Editing, Agent Skills, Memory
  Tool, Agent SDK subagents to NexusForge modules. Includes §12 roadmap +
  §12.1 Feature 1 post-mortem with honest reality-check.
- [`mcp-servers-setup.md`](./mcp-servers-setup.md) — ready-to-activate
  recipes for Render, GitHub, Postgres MCPs + `/schedule` pattern for
  automated changelog checks.

### Historical / diagnostic

- [`IMPLEMENTATION_AUDIT.md`](./IMPLEMENTATION_AUDIT.md) — 2026-03-29
  line-by-line code audit. **Stale** — most P0/P1 items likely fixed since
  (see §4.F verification checklist).
- [`AGENT_AUDIT.md`](./AGENT_AUDIT.md) — 2026-03-30 agent inventory.
  Documents the frontend-vs-backend agent discrepancy (22 UI demo vs 21
  backend real).
- [`architecture-diagram.md`](./architecture-diagram.md), [`design-decisions.md`](./design-decisions.md),
  [`failure-recovery.md`](./failure-recovery.md) — 2026-03-30 snapshots

### Project-level

- `CLAUDE.md` at repo root — always-loaded project context for Claude Code
- `PROJECT_SUMMARY.md` — high-level overview (**stale counts** per §4.A)
- `CHANGELOG.md` — frozen at v2.5.0 2026-04-04 (**stale** per §4.A)
- `README.md` — public-facing description
- `ARCHITECTURE.md` — detailed architecture document

---

## 6. Update protocol

**When to update this file:**

1. **After shipping a Gap** (1-12) — update the status table in §3 with the
   commit ref
2. **After shipping a phase of the Anthropic adoption** — update the Phase
   status in §4.D
3. **When an API key arrives** — move the corresponding item from §4.B to
   §4.A and run the activation
4. **After merging a feature branch** — move from §4.C to "live" in §1 and
   remove the branch from the pending list
5. **When starting a new workstream** that isn't in §2 — add it
6. **On a weekly cadence** — refresh the "last updated" date, even if
   nothing changed, to signal the doc is still the source of truth

**When NOT to update this file:**

- For day-to-day code edits that don't move a phase/gap/PR status
- For changes in the `.claude/` orchestrator config — those are local
  workflow, not part of NexusForge the product
- For research notes that haven't concluded yet — keep them in the
  dedicated research doc until a decision is locked

**Defer to detail docs when:**

- Design rationale for a specific gap → `integration/03_future_platform_vision.md`
- Exact code changes for Feature N → `anthropic-features-research.md`
- MCP activation steps → `mcp-servers-setup.md`
- Phase 2 synthetic generator internals → `integration/02_phase2_plan.md`
- Critical rules → `CLAUDE.md`

---

## 7. Next session kickstart checklist

When Christian opens a new session and asks "what's next?", the honest
answer depends on which constraint is binding:

1. **If API keys have arrived** → work §4.B top-down (Render first, it's
   the highest value)
2. **If PRs from feature branches are still unmerged** → review + merge
   them (§4.C) before starting anything new
3. **If everything is clean and you want to ship something new for the
   showcase** → Gap 6 or Gap 8 from §4.A (data pipeline modernizer or AI
   docs generator) — both are single-session MVPs
4. **If you want to harden the existing platform** → verification pass
   on §4.F stale audit items
5. **If you want to continue the Anthropic adoption** → Phase 3 (Memory
   Tool) from §4.D after the feature branches are merged

Default recommendation if none of the above is urgent: **close out the 2
unmerged feature branches first** (§4.C) so master reflects the full
Feature 1, then pick Gap 6 from §4.A.
