# NexusForge AI — v2.0

## What is this?
Enterprise AI platform for agent orchestration + automated code remediation at scale.
Handles 5.6M LOC, 166K issues, 3K+ SQL injections across 31 apps.
Built for publicly-traded enterprise systems with multi-million-dollar risk exposure.

## Stack
- Backend: Python 3.12 + FastAPI
- Frontend: React 18 + Vite 8
- Database: PostgreSQL 16 + pgvector (semantic memory)
- Document Store: MongoDB 7 (episodic memory)
- Cache/Queue: Redis 7 (working memory)
- Local LLMs: Ollama (qwen2.5-coder:7b, deepseek-r1:8b, llama3.1:8b, gemma3:4b, nomic-embed-text)
- Cloud LLMs: Haiku 4.5 ($1/MTok) + Groq (free) + Claude Opus 4.7 ($5/$25 MTok) + Sonnet 4.6 (cached)
- Auth: Google OAuth + JWT + Stripe billing
- Security: Mythos internal auditor + Fernet encryption
- Deploy: Vercel (frontend) + Render (backend)

## Architecture

### Core Platform (24 agents)
- Chat-first dashboard at / (ChatPanel 60% + PreviewPanel 40%)
- Per-agent model routing: gemma→classification, qwen→code, llama→language, haiku→fast cloud
- LLM fallback: Ollama → Haiku → Groq → Claude (with prompt caching)
- 5-tier memory: working (dict) → episodic (Redis+MongoDB) → semantic (pgvector) → regressive → predictive
- Self-healing: 5 strategies (retry, skip, repair, escalate, fallback) with 120s timeout
- WebSocket execution tracking (useExecutionWS hook)

### Refactoring Engine (enterprise scale)
- Repo Ingestion: clone → detect 10 langs → dependency graph → DAG (2.4s for 616 files)
- C# Analyzer: SQL injection, creds, god classes, auth gaps, shared deps (28 findings in <1s)
- C# Fixer: deterministic (instant, $0) + LLM via Ollama ($0, ~30s)
- Issue Triage: CWE-weighted priority, 7 batches, effort estimation
- Batch Pipeline: 4 parallel workers, 3,726 fixes/hour, auto-rollback
- PII Scanner: 25 types, encryption/masking/retention recommendations
- DB Integrity: FK detection, PII columns, schema analysis, archiving
- Test Generator: pytest/xUnit/Jest (193 files in 203ms)
- CI/CD Generator: GitHub Actions for .NET + Python
- RPA Scanner: Playwright selector stability scoring
- Multi-Repo: 5+ repos in parallel (704 files, 155 tests in 1.9s)
- PR Generator: auto-branch + commit + PR body with metrics

### Security (Mythos)
- Owner-only access via X-Mythos-Key (derived from JWT_SECRET)
- 9 scan categories: secrets, auth, injection, crypto, config, rate_limit, data, deps, frontend
- Fernet encryption for API keys (AES-128-CBC + HMAC)

## Commands
- `cd backend && pytest` — Run 307+ tests
- `cd frontend && npx vite build` — Build frontend (144KB app + 230KB vendor)
- `python test_full_system.py` — Run 17 functional tests (all modules)
- `nexusforge status` — Check all services

## Tests
- 307 unit tests (pytest)
- 17 functional tests (test_full_system.py)
- Tested on: vuln-test (4 files), dotnet-identity (1106 files), eShop (633 files), tenant-alpha synth (128 files), NexusForge (620 files)

## API Endpoints (active)
> Updated 2026-04-30 after the gap-audit triangulation. Source of truth
> is `app.include_router()` calls in `backend/app/main.py`. Endpoints
> grouped by surface. The `/api/v1/*` mirror is a CURATED subset (see
> `_V1_PUBLIC_ROUTERS` in main.py); v0 paths remain available.

### Identity & accounts
- /api/auth/* (login, register, oauth, me, logout, refresh)
- /api/api-keys/* (generate, list, delete)
- /api/billing/* (checkout, webhook, portal)
- /api/organizations/* (org CRUD + memberships)

### Workflow runtime
- /api/workflows/* (CRUD + run)
- /api/executions/* (create, get, WS at /ws/{run_id})
- /api/runs/* (run history, reliability)
- /api/automations/* (publish, schedule, webhook trigger)
- /api/agents/*, /api/swarms/*, /api/documents/*

### Wizard & SDK
- /api/wizard/chat, /api/wizard/generate, /api/wizard/guide, /api/wizard/questions
- /api/sdk/run, /api/sdk/review, /api/sdk/research, /api/sdk/batch

### Refactor engine
- /api/refactor/ingest, /execute, /triage, /batch-remediate
- /api/refactor/analyze-csharp, /fix-csharp, /generate-cicd
- /api/refactor/scan-pii, /scan-db, /scan-rpa, /generate-tests, /scan-multilang
- /api/refactor/multi-repo, /pr, /status

### Use cases (analyze, intelligence)
- /api/analyze/*, /api/analyze/text (Form-encoded)
- /api/enterprise-ops/* (POST /process expects {message, language})
- /api/document-intelligence/* (POST /run expects {content, language, filename})
- /api/portfolio-copilot/run, /examples, /health  (wired 2026-04-30)
- /api/evaluation/* (scenarios, runs, results — wired 2026-04-30)
- /api/executions-db/* (DB-backed timeline + checkpoints — wired 2026-04-30)
- /api/orchestrator/* (agent memory control plane — wired 2026-04-30)
- /api/meta/* (pipeline, reason, generate-spec, predict-features, optimize-flow,
  sdk/run, sdk/review, sdk/research — wired 2026-04-30)

### Operational / integration
- /api/integrations/*, /api/connectors/*, /api/templates/*, /api/rules/*, /api/variables/*
- /api/feedback/*, /api/drive-pipeline/*
- /api/audit/* (compliance audit log + entity trail + CSV export)
- /api/activity/*, /api/activity/summary  (per-user token / cost feed —
  formerly mounted at /api/audit/, moved 2026-04-30 to stop a
  prefix-shadow bug; see app/auth/audit.py docstring)
- /api/metrics/*, /api/health, /api/demo/*

### Security (Mythos — owner-only)
- /api/mythos/scan, /api/mythos/scan/{category}, /api/mythos/scan/diff
- (no public /api/mythos/key — H-3 closed 2026-04-25)

### Admin (admin-only, 404 to non-admin per info-leak guard)
- /api/admin/dashboard, /api/admin/users, /api/admin/orgs, /api/admin/usage, /api/admin/audit
- /api/admin/users/{id}/refresh-tokens/revoke-all
- /api/admin/security/fernet-rotation/global, /api/admin/security/fernet-rotation/tenant

## Frontend Routes
- / (ChatFirst), /automations, /wizard, /workflows, /executions
- /agents, /swarms, /integrations, /connectors, /settings
- /analyze, /intelligence, /audit, /metrics, /status, /docs
- /refactor (Refactoring Dashboard)
- /executive (Executive C-Level Dashboard)

## Critical Rules
- NEVER use PUT on Render /env-vars API without ALL existing vars
- NEVER modify existing encapsulated components — add new ones alongside
- NEVER delete Vercel projects that own active domain aliases
- NEVER remove useEffect from imports without checking other usages in file
- Quality over speed — read files before changing, build before pushing
- Frontend .jsx required for files with JSX (Vite 8 strict)
- Rollback immediately on deploy errors, don't fix forward

## Deploy
- Frontend: nexusforge-two.vercel.app (manual via vercel --prod)
- Backend: nexusforge-api.onrender.com (auto-deploy from master)
- Portfolio: ch65-portfolio.vercel.app
- Repo: PRIVATE (christianescamilla15-cell/nexusforge-ai)

## Conventions
- English for code, Spanish for user-facing strings
- Pydantic v2 for all models
- Type hints on all functions
- Chat system prompt: friendly, ONE question at a time, no JSON to user
