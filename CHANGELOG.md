# Changelog — NexusForge AI

## v2.6.0 (2026-04-11)

**Headline:** 212 commits since v2.5.0 across the Anthropic 4-feature
adoption roadmap, the Platform gap closure (10 of 12 shipped), the
tenant-alpha public showcase, the synthetic generator Batch 3 + Phase B
scaffolding, and a full audit closure (7 of 7 P0/P1 items).

Tests: 260 → **616** (+356 tests, all green on the default suite).
`test_full_system.py` remains excluded due to a pre-existing collection
error from a missing external-repo path.

### Anthropic features adoption (Phases 0-5a shipped, 5b in progress)

Phases track `docs/anthropic-features-research.md`. Phase numbering is
stable across sessions; Phase 6 (Mythos upgrades) remains ahead.

- **Phase 0** — `anthropic` SDK bumped from 0.34.0 → 0.94.0 to unlock
  the Context Editing beta. Validated out-of-tree in a throwaway venv
  before the pin was merged.
- **Phase 1+2** (Feature 1 — Context Editing) — `context_management`
  kwarg plumbed through `llm/provider.py`, `claude_provider.py`,
  `haiku_provider.py`, `ollama_provider.py`, `groq_provider.py`, and
  `router.py`. `_fix_claude_batch` in the refactor batch pipeline
  rewritten from a stub to a real Claude call with Context Editing
  enabled for long batch runs. 9 new tests in `test_context_editing.py`.
- **Phase 3** — `MemoryToolHandler` + `run_memory_loop` agent-loop
  helper shipped in `backend/app/memory/anthropic_memory_tool.py` and
  `backend/app/llm/agent_loop.py`. `ComplianceAgent` and
  `PlannerAgent` both opt into the memory loop via
  `NEXUSFORGE_MEMORY_TOOL_COMPLIANCE=1` and
  `NEXUSFORGE_MEMORY_TOOL_PLANNER=1` respectively (default OFF,
  production byte-identical). Per-agent memory scoping with
  directory-traversal protection, 1 MB file cap, memory-poisoning
  safety preamble.
- **Phase 4** — Agent SDK subagent memory. `AgentDefinition.memory="project"`
  passed to all 4 NexusForge subagents (security-auditor, code-reviewer,
  test-engineer, architect) when the installed SDK supports the kwarg
  (probed once at import time). Redis-backed session persistence at
  `nexusforge:sdk:session:{user_id}:{agent_name}` with a 7-day TTL.
  New `AgentSDKBridge.resume()` method and `POST /api/sdk/resume/{agent_name}`
  endpoint. Render ephemeral-FS caveat documented in
  `docs/DEPLOYMENT.md §Production`.
- **Phase 5a** — Agent Skills loader infrastructure. New
  `backend/app/agents/skill_loader.py` that parses `SKILL.md` files
  with a naive YAML frontmatter parser (no PyYAML dep). Path safety,
  graceful degradation, per-instance cache, singleton accessor.
  `BaseAgent._build_system_prompt_v2` falls back byte-identical to
  the legacy method when a skill is missing or when
  `NEXUSFORGE_SKILLS_DISABLED=1` is set (emergency rollback).
  `GET /api/agents/skills` endpoint lists available skills.
- **Phase 5b PR 1** — `ClassifierAgent` migrated to
  `_build_system_prompt_v2`. First real migration on top of the 5a
  infrastructure. ComplianceAgent, PlannerAgent, the 4 Agent SDK
  subagents and 19 more agents remain on the legacy path and will
  land as individual follow-up PRs.

### Refactoring engine — Platform gaps (10 of 12 shipped)

Gap numbers trace back to `docs/ROADMAP.md §2`.

- **Gap 1** — Multi-language vulnerability scanner (Python, JS/TS,
  Java, PHP, Go, Ruby) on top of the existing C# analyzer.
- **Gap 2** — COBOL scanner + FastAPI wrapper generator for the
  mainframe core-wrap pattern.
- **Gap 3** — Phase 4 strangler-pattern migration planner that
  honors pre-assigned `RefactorDecision` classifications from the
  synth fixtures instead of re-deciding at plan time.
- **Gap 4** — IaC generator (Terraform modules + Helm charts +
  kustomize overlays) for the refactor pipeline output.
- **Gap 5** — GitFlow governance template generator.
- **Gap 6** — Data pipeline modernization planner.
- **Gap 7** — Compliance-by-design enforcer (auth / rate-limit /
  encryption middleware templates).
- **Gap 8** — AI-powered documentation generator.
- **Gap 11** — Observability stack bootstrapper (Prometheus +
  OpenTelemetry config scaffold).
- **Gap 12** — Post-modernization knowledge transfer mode. A
  persistent tech-lead-style agent that stays active after the
  refactor delivery to mentor the internal team, leveraging the
  Agent SDK bridge and memory tiers.

Remaining: Gap 9 (vendor lock-in escape analyzer) and Gap 10
(encrypted data pipeline scaffolder) — both explicitly deferred as
long-term post-MVP.

### Audit closure — 7 of 7 P0/P1 items now resolved

Against `docs/IMPLEMENTATION_AUDIT.md` (2026-03-29):

- **P0 #1** Self-healing wired into `step_runner.py` — ✅ FIXED.
- **P0 #2** Observability unified via `ctx.tracker` — ✅ FIXED.
- **P0 #3** Frontend dashboard fetches real data — ✅ FIXED.
- **P1 #4** Migration runner exists and is hardened on failure — ✅ FIXED.
- **P1 #5** State machine enforced — ✅ **FIXED this release** in
  `2666a84`. `transition_workflow` / `transition_step` now called at
  every status-write site in `executor.py` and `step_runner.py`, with
  a locally-tracked `current_status` variable. Multi-retry flows stay
  legal via a `retrying → running` normalization. `QUEUED → FAILED`
  added to the workflow state machine (pre-run DAG validation error
  path). 4 new unit tests.
- **P1 #6** Memory used by agents during execution — ✅ FIXED.
- **P1 #7** Auth middleware enforcing routes — ✅ FIXED.

The audit doc remains in the repo as historical context, annotated
with a verification banner at the top pointing at
`ROADMAP.md §4.F` as the canonical closed-state record.

### Tenant Alpha public showcase (Batch 3)

Full-fidelity showcase dashboard at `/showcase` with backend
persistence, mobile responsive tuning and a non-technical stakeholder
view of the modernization program.

- Public tenant showcase dashboard (backend data + frontend).
- Compliance countdown card with per-certification status (SOX,
  SOC 2, data privacy) tracking the hard deadline.
- Commercial risk profile card — vendors, contract coverage,
  penalty exposure, lock-in level.
- Governance profile card — steering committee, teams, code access
  gate, post-launch tech-lead slot.
- Refactor decision badges on app cards (REFACTOR / RETIRE /
  RETAIN / TBD).
- Report Out simulator — single-document stakeholder deliverable
  that summarizes findings, decisions, commercial risk and
  governance in one view.
- Persist runs in PostgreSQL with a static fallback path for
  unauthenticated preview.
- Parallel core workstream artifact (Batch 3 deliverable E) —
  cross-cutting workstream that coordinates shared-library changes
  across multiple apps.
- Demo video script walkthrough documented.
- Mobile responsive pass — sidebar hamburger fix, bottom-nav
  overlap fix, table reflow on narrow viewports, Google OAuth
  button visibility fix.

### Synthetic generator (Batch 3 + Phase B scaffolding)

- **Phase 2 MVP** — tenant-alpha 5-app fixture with per-app
  recipes (language mix, LOC target, vulnerability density, sub-
  projects, databases, decisions).
- **Batch 3 realism upgrade** — `sub_projects` arrays for multi-
  stack apps, `inject_legacy_db_schema` for 0-FK schema fixtures,
  `db_inactive_since` flag for retirement candidates,
  `inject_god_method_cc: 150` for realistic cyclomatic complexity.
- **Phase B scaffolding** (this release) — 5 scope apps → 31-app
  tenant footprint via `non_scope_apps` stubs. Each non-scope app
  gets a single `DISCOVERY_PENDING.md` file with a codename,
  short label, category tag and free-form notes. No fabricated
  code, no fabricated vulnerability counts — the 5 scope apps
  stay the authoritative source for findings totals. Categories:
  satellite / shared-library / archival / utility / integration.
- `--scale` flag on `generator.py` for LOC multiplication
  (targeting 5.6M LOC full-ecosystem scale).
- Cyclomatic complexity injection module.
- Commercial risk, governance and compliance profile sections in
  the YAML fixture loader.

### Infrastructure / hardening

- Migration runner hardened — unblocks migration 031
  `CREATE POLICY` path + fails loudly on any intermediate error
  (previously silent).
- Security sanitization pass — all client-identifying references
  removed from code and docs per the confidentiality rule.
- FastAPI `/docs` and `/openapi.json` gated behind
  `settings.debug` flag.
- `conftest.py` sets fake env vars to unblock CI test collection
  on a fresh clone.
- CHANGELOG root refresh (this file) — captures the 212 commits
  since v2.5.0.
- ROADMAP.md synced — `§4.A` ready-now follow-ups struck through,
  `§4.D` Anthropic phases table updated to 0-4 shipped + 5a
  shipped, `§4.F` audit outcome bumped from "6 of 7" to "7 of 7".

### Developer tooling / docs

- `docs/anthropic-features-research.md` — 1175-line research
  document mapping the 4 Anthropic features to NexusForge modules
  line-by-line, with per-phase upgrade paths and effort
  estimates.
- `docs/integration/01_agent_mapping.md`,
  `02_phase2_plan.md`, `03_future_platform_vision.md` — strategy
  documents for the tenant-alpha integration, Phase B scale and
  end-state enterprise architecture vision.
- `docs/mcp-servers-setup.md` — ready-to-activate recipes for
  Render / GitHub / Postgres MCP servers.
- `docs/DEPLOYMENT.md §Production` — Render ephemeral-FS caveat
  documented with mitigations and future Phase 4.1 externalization
  path.
- New NexusForge subagents for Claude Code: Mythos auditor,
  refactor triager, test runner, deployer.
- `nexusforge-validate-bump` skill for out-of-tree dependency
  validation.
- `py_compile` pre-commit hook live-verified on every commit.
- New skill: `nexusforge-research` (structured research workflow
  for evaluating new Anthropic features against NexusForge).
- New skill: `nexusforge-status` (one-shot snapshot of git / deploy
  / service state).
- New skill: `orchestrate-agents` (coordinate the 24 agents for
  complex tasks).
- New skill: `route-to-specialist` (pick the optimal agent for a
  given task type / complexity / cost).
- New skill: `audit-memory` (5-tier memory health check).

### Stats

- **212 commits** since v2.5.0 (2026-04-04)
- **24 agents** (unchanged count, but ClassifierAgent now uses
  the Agent Skills loader path)
- **616/616 tests** passing on the default backend suite
- **31 apps** in the tenant-alpha synthetic footprint (5 scope + 26
  discovery-pending stubs)
- **7/7 audit items** closed
- **Phases 0, 1, 2, 3, 4, 5a** of the Anthropic adoption roadmap
  shipped; **Phase 5b PR 1** (ClassifierAgent) shipped; Phases 5b
  remainder + 6 ahead
- **10/12 Platform gaps** shipped (Gaps 9 and 10 deferred as
  long-term post-MVP)

---

## v2.5.0 (2026-04-04)

### Superagent Upgrades (24 agents)
- All 24 agents upgraded with deterministic layers + LLM fallback
- `clean_llm_json()` handles markdown fences across all agents
- Pydantic v2 output schemas for 6 agents
- CircuitBreaker wired into BaseAgent.run()
- Tenacity retry catches all transient exceptions
- 6 critical bugs fixed (fail-open critic, EMA variance, DD/MM dates, etc.)

### New Pages
- Intelligence Hub (Enterprise Ops + Doc Intel + Analyze)
- System Status (real-time health of all components)
- API Docs (Swagger link + auth reference)
- Custom 404 page

### Auth & Security
- Email verification (OTP via Resend)
- Forgot Password flow (email code + reset)
- Change Password
- Google OAuth button
- Session expiry warning (5 min before JWT expires)
- Rate limiting per plan (Free 5, Pro 100, Team 500)
- RBAC ownership checks on DELETE endpoints
- API key encryption (XOR+HMAC)
- GDPR data export (JSON download)
- CORS configurable via env vars
- DEBUG=false by default

### UX Features (28 batches)
- React Router (URL-based navigation, deep linking)
- Code splitting (712KB → 342KB, 19 lazy chunks)
- Command Palette (Ctrl+K) with Quick Run automations
- Keyboard shortcuts (?, Ctrl+Enter, Esc)
- Getting Started checklist with completion celebration
- What's New changelog modal
- PWA manifest (installable on mobile)
- Dark mode for all components
- Top loading bar on route transitions
- Offline indicator
- Connection status dot in header
- Tab title with notification count + dynamic page names
- Window focus refetch (30s stale threshold)
- Skeleton loaders
- Sparkline + MiniBarChart components
- ConfirmModal (9/9 native confirms replaced)
- ErrorBoundary crash recovery
- Time-based greeting ("Good morning, Christian")
- Last page redirect on login
- Auto-refresh Dashboard (30s)

### Automations
- Search + pagination (12/page)
- Edit modal (name, description, trigger)
- Clone/duplicate
- Favorites (star + sort)
- Batch select + delete with Select All
- Share URL (clipboard)
- Schedule picker (presets + custom cron)
- Run notifications in all 5 dashboards
- CSV export for results
- Relative time (timeAgo)

### Dashboard
- Quick Actions (4 shortcut buttons)
- Plan usage bar
- Runs-per-day bar chart
- Getting Started checklist
- Auto-refresh with "updated ago" indicator
- KPI labels bilingual (ES/EN)
- Feedback widget (star rating)
- Platform stats in subtitle

### Workflows
- Export as JSON
- Import from JSON
- Duplicate
- Toast feedback on delete/rename

### Infrastructure
- Redis Upstash (TLS) on Render
- Zombie cleanup (auto every 5 min)
- Feedback persisted to PostgreSQL (migration 025)
- Email verified column (migration 026)

### Components Created (40)
IntelligenceHubPage, StatusPage, ApiDocsPage, CommandPalette, ConfirmModal, WhatsNew, KeyboardShortcuts, Skeleton, ErrorBoundary, Breadcrumb, CopyButton, TopLoadingBar, OfflineIndicator, SessionExpiry, Sparkline, MiniBarChart, GettingStarted, FeedbackWidget, SchedulePicker, NotFoundPage, ConnectionDot, EditAutomationModal, PlanUsageBar, BillingSection, AccountSection, TestAgentSection, EmptyState, manifest.json, useConfirm, useCopyClipboard, useCtrlEnter, useRefreshOnFocus, useTabTitle, timeAgo, clean_llm_json, output_schemas, circuit_breaker, encryption, deps, migrations

### Stats
- 106 modules, 260/260 tests, 16 pages, 342KB bundle
