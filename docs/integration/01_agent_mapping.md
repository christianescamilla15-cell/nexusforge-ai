# Agent Mapping — External Engagement → NexusForge

**Status:** Draft — Phase 1 of integration
**Owner:** Christian Hernandez (sole admin)
**Date:** 2026-04-10

## Purpose

This document maps the 6-agent system from an external private engagement repo
(hereafter: **external repo**) to NexusForge's existing 23 agents + refactor
engine modules, so we can execute the engagement entirely inside NexusForge
without duplicating code.

## Strategic context (updated 2026-04-10)

Tenant-alpha is a **showcase** — NOT a real refactor of live client code. No
code access exists or will exist. Instead, NexusForge will ingest a
**synthetic codebase** generated deterministically to match the external
engagement's structural parameters (language mix, DB mix, vulnerability
density, LOC scale).

**Scale path:**
- **Phase A (this work):** 5 synthetic apps (~900K LOC)
- **Phase B (follow-up):** scale to 31 synthetic apps (~5.6M LOC)

**Value prop to prove in the demo:** NexusForge modernizes 5.6M LOC / 31
apps in **weeks, not years**. Every piece of code and doc below serves this
single metric.

## Confidentiality Scheme

Per project policy, **no real client / vendor / people / system names appear
in NexusForge**. The external repo is referenced abstractly; all user-facing
and code-level names use generic codenames:

| Concept | Codename used in NexusForge |
|---|---|
| Client organization | `tenant-alpha` (display: "Alpha Corp") |
| Engagement team | "engineering team" (no vendor names) |
| Target app #1 — fiscal reconciliation | `app-01` / "Transaction Reconciliation Service" |
| Target app #2 — batch sales mgmt | `app-02` / "Batch Sales Management" |
| Target app #3 — refund automation (Python + Playwright) | `app-03` / "Automated Refund Processing" |
| Target app #4 — document batch ingest | `app-04` / "Document Batch Ingestion" |
| Target app #5 — commission engine (C# + Cobol + multi-DB) | `app-05` / "Commission Engine" |
| Legacy vendor platform | "legacy host platform" |
| Internal shared components | "shared legacy library" |

Stack details (C#, .NET, Python, Cobol, MySQL, DB2, SQL Server, Oracle) are
generic and may appear as-is. Industry sector is **not** disclosed.

## External Repo — 6 Agents + Tri-layer Memory

Source: `external-repo/agents/` + `external-repo/orchestrator/smart_orchestrator.py`

| # | External agent | Role |
|---|---|---|
| E1 | `CodeAnalystAgent` | Detect OWASP vulnerabilities + technical debt |
| E2 | `RefactorAgent` | Generate refactored code preserving business logic |
| E3 | `TestGeneratorAgent` | Create unit + integration tests |
| E4 | `ArchitectAgent` | Migration plans, cross-module impact |
| E5 | `SpeculativeAgent` | Predict dependencies, pre-process context |
| E6 | `MultiLLMAgent` | Route tasks to optimal provider |
| E+ | `SecurityAgent` (alongside) | Pattern-based local vulnerability scan |
| E+ | `AppScanner` (tool) | Walk repo, classify files |

Memory: 3-layer (persistent / regressive / speculative) under
`external-repo/memory/` with an `index.json` catalog.

## NexusForge — Current Capabilities

**Classic agents (23 files in `backend/app/agents/`):**
analyzer, classifier, compliance, critic, enricher, extractor, judge,
knowledge, monitor, normalizer, ocr, planner, repair, reporter, researcher,
router, scheduler, scraper, sentiment, summarizer, translator, validator,
webhook.

> Note: `CLAUDE.md` claims "24 agents" but the filesystem currently has 23.
> This is a minor discrepancy to reconcile later — no impact on mapping.

**Refactor engine modules (`backend/app/refactor/`):**
`ingestion`, `csharp_analyzer`, `csharp_fixer`, `llm_fixer`, `pii_scanner`,
`db_analyzer`, `test_generator`, `cicd_generator`, `rpa_scanner`,
`multi_repo`, `triage`, `batch_pipeline`, `rollback`, `pr_generator`,
`engine`.

**Security / scanning:** `backend/app/mythos/` (9 scan categories).

**Memory (5-tier):** working → episodic → semantic (pgvector) → regressive
→ predictive.

## Mapping Table

Each external agent maps to **one or more** existing NexusForge components.
No external agent code needs to be ported — we reuse NexusForge's equivalents.

### E1 — CodeAnalystAgent → NexusForge composite

| Capability | NexusForge component | Notes |
|---|---|---|
| C# SQLi / creds / god classes | `refactor/csharp_analyzer.py` | Deterministic, <1s for 1K files |
| Python / PHP / Java SQLi | **gap** — needs extension of csharp_analyzer to multi-lang, or use Mythos pattern rules | Phase 2 |
| PII detection (25 types) | `refactor/pii_scanner.py` | Ready |
| DB integrity / FK / schema | `refactor/db_analyzer.py` | Ready |
| General semantic analysis | `agents/analyzer.py` (llama3.1) | Ready |
| Regulatory / compliance checks | `agents/compliance.py` (Claude-only) | Ready |
| Secrets / auth / crypto / config scan | `mythos/` (9 categories) | Ready, owner-only |

**Ported code:** none. **Gap:** multi-language SQLi analyzer (Python/PHP/Java).

### E2 — RefactorAgent → NexusForge composite

| Capability | NexusForge component | Notes |
|---|---|---|
| Deterministic C# fixes | `refactor/csharp_fixer.py` | Instant, $0 |
| LLM-driven fixes (Ollama) | `refactor/llm_fixer.py` | ~30s/file, $0 |
| Parallel batch remediation | `refactor/batch_pipeline.py` | 4 workers, 3,726 fixes/h, auto-rollback |
| Structured repair | `agents/repair.py` (qwen2.5-coder) | For JSON / schema fixes |
| Rollback on failure | `refactor/rollback.py` | git stash checkpoint |

**Ported code:** none. **Gap:** Python / Cobol / PHP fixers (currently C#-only deterministic).

### E3 — TestGeneratorAgent → NexusForge direct

| Capability | NexusForge component | Notes |
|---|---|---|
| pytest / xUnit / Jest gen | `refactor/test_generator.py` | 193 files in 203ms |
| Validation of generated tests | `agents/validator.py` (qwen) | Ready |

**Ported code:** none. **Gap:** none — identical capability.

### E4 — ArchitectAgent → NexusForge composite

| Capability | NexusForge component | Notes |
|---|---|---|
| Dependency graph + DAG | `refactor/ingestion.py` | 2.4s for 616 files |
| Cross-module impact analysis | `refactor/triage.py` | CWE-weighted, 7 batches |
| High-level migration planning | `agents/planner.py` (Groq→Claude) | Cloud-preferred |
| Research / context gathering | `agents/researcher.py` (Groq→Claude) | Ready |

**Ported code:** none. **Gap:** cross-module "god class" impact simulator for shared legacy libraries (needs small extension to triage).

### E5 — SpeculativeAgent → NexusForge composite

| Capability | NexusForge component | Notes |
|---|---|---|
| Prediction over past patterns | Memory tier 5: predictive | Ready |
| Dependency pre-fetch | `refactor/ingestion.py` DAG + semantic tier | Ready |
| Task routing decisions | `agents/router.py` (gemma) | Ready |
| Knowledge recall | `agents/knowledge.py` (qwen) | Ready |

**Ported code:** none. **Gap:** the external repo's predictive heuristics (from `memory/speculative/`) should be imported as seed data into NexusForge's predictive tier — one-time migration, not code.

### E6 — MultiLLMAgent → NexusForge direct

| Capability | NexusForge component | Notes |
|---|---|---|
| Provider routing | LLM fallback chain | Ollama → Haiku → Groq → Claude |
| Per-agent model binding | Agent registry | gemma/qwen/llama/haiku |
| Cost optimization | HaikuProvider + prompt caching | 90% savings |
| Batch API cost optimization | `/api/sdk/batch` | 50% savings |

**Ported code:** none. **Gap:** none — NexusForge is strictly more capable.

### E+ — SecurityAgent → Mythos

Direct equivalence to `backend/app/mythos/` which has 9 scan categories.
The external `security_agent.py` uses simpler pattern matching; Mythos is
strictly a superset. **No port needed.**

### E+ — AppScanner → ingestion engine

Direct equivalence to `refactor/ingestion.py` + `refactor/multi_repo.py`.
**No port needed.**

## Memory Mapping

| External layer | NexusForge tier | Migration approach |
|---|---|---|
| `memory/persistent/` (facts JSON) | Tier 3: semantic (pgvector) | One-shot import script, embed facts as vectors |
| `memory/regressive/` (lessons) | Tier 4: regressive | Direct JSON-to-record import |
| `memory/speculative/` (predictions) | Tier 5: predictive | Direct import as seed heuristics |
| `memory/subagents/` (per-agent memory) | Tier 1 + 2: working + episodic | Import only active / recent entries |
| `memory/index.json` | Rebuilt from NF's own indexer | Discard original |

**Migration script location:** `backend/scripts/import_external_memory.py`
(to be written in phase 3). Will read from a local clone of the external
repo (path configured per-admin, never committed).

## Net Gap Summary

Capabilities NexusForge is missing for this engagement:

1. **Multi-language SQLi analyzer** — extend `csharp_analyzer` or add
   `python_analyzer`, `php_analyzer`, `java_analyzer`. (~1 day each)
2. **Python / Cobol / PHP deterministic fixers** — extend `csharp_fixer`
   pattern. Cobol is the hardest (may need LLM-only via Ollama).
3. **Shared-library impact simulator** — small extension to `triage.py`
   to model "god class used by N modules" cascading risk.
4. **Import tool for external memory** — one-off migration script.

Everything else = already in NexusForge, **zero porting**.

## What Stays in the External Repo

- All client-specific documentation, findings, sessions, BIAs, Excel reports
- The 25+ `gen_*.py` document generators (PM deliverables)
- Raw memory files (as source of truth for the migration)
- `.kiro/steering.md` with client-specific constraints

NexusForge will pull these via a thin **tenant connector** (phase 2) that
clones the external repo with a per-admin token, reads SCOPE.md and
steering.md, and injects them as tenant config — without ever committing
real names to NexusForge.

## Phase 1 Deliverable (this document)

- [x] Confirmed both repos are private
- [x] Confidentiality rule documented
- [x] 6 external agents mapped to NexusForge components
- [x] Memory layers mapped
- [x] Gaps identified

## Next Phases

- **Phase 2** — Tenant setup (`tenant-alpha` in NexusForge DB, Christian as
  sole admin) **+ synthetic codebase generator** that produces deterministic
  fake legacy code matching the real parameter profile (languages, DBs,
  vulnerability density). See [02_phase2_plan.md](./02_phase2_plan.md).
- **Phase 3** — Gap 1: multi-language SQLi analyzer (extend
  `csharp_analyzer` to Python/PHP/Java). Required so detection works on
  synthetic code in all languages.
- **Phase 4** — End-to-end run on all 5 synthetic apps. Measure ingest
  time, detection count, remediation time. Publish metrics on `/executive`
  dashboard for the tenant.
- **Phase 5** — Scale to 31 synthetic apps (~5.6M LOC). Stress-test the
  batch pipeline. Measure "weeks not years" claim with concrete numbers.
- **Phase 6** — Recorded demo + landing page proof.

## Decisions locked in (2026-04-10)

1. Codenames: `tenant-alpha`, `app-01..05`, labels approved ✓
2. Tenant name: `tenant-alpha` / "Alpha Corp" ✓
3. Gap priority: multi-lang SQLi analyzer (must-have). Memory importer
   becomes irrelevant (no real memory to import — synthetic data only).
   God-class impact sim and Python/Cobol fixers deferred to phase 5+.
4. No real code access. 100% synthetic from day one. Synthetic code must
   replicate the real profile (5.6M LOC total, 8 langs, 6 DBs, ~3K SQLi,
   166K issues). ✓
