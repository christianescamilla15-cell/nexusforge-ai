# Phase 2 Plan — Tenant Setup + Synthetic Codebase Generator

**Status:** Draft — awaiting approval before coding
**Depends on:** [01_agent_mapping.md](./01_agent_mapping.md)
**Date:** 2026-04-10

## Goal

Get `tenant-alpha` fully set up in NexusForge with 5 synthetic apps ready to
be ingested and analyzed by the existing refactor engine. No real code
involved. Deterministic, reproducible, demo-ready.

## Deliverables (in order)

### 1. Tenant bootstrap
- Create `tenant-alpha` org in NexusForge DB via seed / migration
- Christian as sole `owner` role, email-linked
- 5 empty "project" records (app-01 .. app-05) with stack metadata
- Row-level security verified (no other tenant can see)

### 2. Synthetic codebase generator (new module)

**Location:** `backend/app/synth/` (new)

**Module layout:**
```
backend/app/synth/
├── __init__.py
├── generator.py         # top-level entry: generate_tenant(config) -> tree
├── profile.py           # parameter profile (5.6M LOC, lang mix, issue density)
├── languages/
│   ├── __init__.py
│   ├── csharp.py        # C# .NET legacy patterns
│   ├── python.py        # Python + Playwright legacy patterns
│   ├── vbnet.py
│   ├── java.py
│   ├── php.py
│   ├── typescript.py
│   ├── cobol.py
│   └── cpp.py
├── databases/
│   ├── __init__.py
│   ├── sqlserver.py     # schema with 97% no FK, PII columns
│   ├── mysql.py
│   ├── db2.py
│   ├── oracle.py
│   ├── sqlite.py
│   └── redis.py
├── vulnerabilities/
│   ├── __init__.py
│   ├── sql_injection.py # concat patterns, target: 3K across apps
│   ├── hardcoded_creds.py # JWT, SMTP, DB strings
│   ├── weak_crypto.py   # MD5/SHA1
│   ├── command_injection.py # PHP exec/popen
│   ├── missing_fk.py    # schema-level
│   └── pii_leak.py      # 25 PII types in 318 inputs
├── structure/
│   ├── __init__.py
│   ├── app_builder.py   # builds a full fake app directory tree
│   ├── god_class.py     # shared lib used by 3+ modules
│   └── no_tests.py      # ensures tests/ is absent or empty
└── fixtures/
    └── app_configs.yaml # per-app recipe: lang mix, LOC target, issue density
```

**Key properties:**
- **Deterministic:** seeded RNG (seed = tenant_id + app_id) so each run
  produces identical output. Essential for recorded demos.
- **Realistic:** vulnerabilities match actual patterns the refactor engine
  already detects (avoid generating fake-looking syntax).
- **Scalable:** `profile.py` accepts an LOC target; generator fills up to it.
- **Fast:** 5 apps (~900K LOC) should generate in under 30s so iteration is
  tight.

### 3. Per-app recipes (phase A — 5 apps)

All recipes are in `fixtures/app_configs.yaml`. Profiles chosen to match
the real engagement's structural mix while staying fully generic.

> **Supersedes prior estimates.** The numbers below come from the
> corrected vendor Report Out captured in
> [`03_future_platform_vision.md`](./03_future_platform_vision.md)
> §15 (Batch 3). Older drafts of this plan used pre-Report-Out
> estimates (180K for app-01, 150K for app-02, 120K monolith for app-04,
> 370K for app-05 with a fabricated stack) — those are no longer
> authoritative. When this table and `03_future_platform_vision.md`
> disagree, `03` wins; update this file to match.

| Codename | LOC | Code findings | DB findings | BLOCKER | CRITICAL | Stack | Notes |
|---|---|---|---|---|---|---|---|
| app-01 | **65,018** | 26 | 22 | 2 | 6 | C# ASP.NET .NET Framework 4.6.1 + Aurora MySQL + S3 | 51 tables, **0 FK**, 71 stored procedures (67 stale since a 4-year-old baseline), 594 MB, 1M+ rows. Site-level WAF only, code NEVER audited. Single-tenant ops tool with ~5-6 concurrent users. |
| app-02 | ~40K | 5 | — | 2 | 3 | C# .NET + SQL Server | Best-documented app in the scope; lowest remediation risk. Used as the "baseline control" app. |
| app-03 | ~80K | 13 | **DB INACTIVE (~2.5 years)** | 5 | 8 | Python + Playwright (RPA), ~500 req/day, window 08-20h | **Retirement candidate** — vendor recommends decommission pending dual validation (technical exploit viability + business ownership confirmation). Generator must emit a `refactor_decision.md` stub set to `action: retire, status: tbd`. |
| app-04 | **~213K total** across 3 sub-projects | 210 | — | 6 | 3 | Java analytics + Python RPA + TypeScript REST frontend + SQL Server | **NOT a monolith — 3 sub-projects**, highest BLOCKER density. Test coverage **0%**. Max cyclomatic complexity **153**. Generator must emit the 3 sub-projects under `app-04/{analytics,rpa,frontend}/`, not a single tree. |
| app-05 | **UNKNOWN** | — | — | — | — | C# + Cobol + Java + 4 DB engines (mixed) | **Not analyzed by vendor — discovery phase required.** Generator should emit an `app-05/DISCOVERY_PENDING.md` stub with placeholder structure and `action: tbd` decision gate, so the refactor engine correctly flags it as "scope requires discovery". |

**Phase A totals (corrected):**
- ~400K LOC across the 5 tenant-alpha scope apps (not 900K as earlier
  estimated). Plus the "nexus app" referenced in
  `03_future_platform_vision.md` §15 (~161K+ LOC, 2,238 findings,
  4 sub-projects across 4 languages, 4 DB engines, cross-team
  coupling) which is **scope-adjacent, not in the 5-app scope** but
  should optionally be generable for full-ecosystem demos.
- The **~3K SQL injection** and **166,714 total issue** numbers in
  `03_future_platform_vision.md` are whole-ecosystem (31 apps + 57
  components, 5.6M LOC), NOT phase A alone. Phase A should target a
  proportional slice — rough allocation: ~800 SQLi, ~15K issues
  distributed across the 5 scope apps per the BLOCKER/CRITICAL counts
  in the table above.

### 3.1. External validator fixture — "failing dependency" pattern

**New in this revision** (2026-04-10 session). Required to model a
real dependency discovered in the app-01 workshop: apps call out to
an **externally-owned validation service** (XML → tax authority) that
has no retry, no queue, no circuit breaker, no fallback. On failure,
batches die half-completed and require manual user re-execution.

**Generator requirement:**

Every synthetic app in phase A (except `app-03` which is retirement-
flagged) must emit a module that calls a mocked `ExternalValidator`
service with these properties:

- Interface: **HTTP REST POST** to `https://validator.example.invalid/validate`
  (the URL must be unreachable-looking so nobody hits it by accident).
- Failure modes to inject: random 500 errors (~5% rate), timeouts,
  malformed response bodies.
- **No resilience patterns**: the generated code has no try/except on
  the call itself, no retry decorator, no `tenacity.retry`, no
  circuit breaker. A bare call followed by direct use of the response.
- Naming: the generated symbol should be plain `ExternalValidator`
  or `external_validator.validate(...)` — **no client-specific name**.
- Finding detection: the refactor engine should flag this as
  **"blocking external dependency without resilience"** when ingested.

**Why this matters for the demo**: the refactor engine's current value
prop is "find + fix code issues". Modeling organizational debt like
missing resilience patterns around external dependencies expands the
value prop to "find + fix architectural debt that blocks operational
stability". This is what `03_future_platform_vision.md` §15.6 and §11
describe as the end-state enterprise architecture goal ("API-first,
event mesh, real-time reconciliation"). NexusForge needs to detect
the current-state gap before it can recommend the target-state fix.

**Implementation pointer:** add
`backend/app/synth/vulnerabilities/blocking_external_dep.py` alongside
the existing SQLi / hardcoded-creds / weak-crypto modules, and wire it
into the per-app recipe via `app_configs.yaml`:

```yaml
app-01:
  ...
  vulnerabilities:
    - sql_injection: 600
    - hardcoded_creds: 12
    - blocking_external_dep:
        count: 1
        endpoint: "https://validator.example.invalid/validate"
        failure_rate: 0.05
```

### 3.2. No-dev-environment fixture — "production-only" pattern

**New in this revision** (2026-04-10 session). Required to model the
blocker identified in the app-01 workshop: **the real target apps
have no dev/QA environment at all**. Deploys are manual, direct to
production, with 5-6 concurrent users. This is a hard constraint on
any refactor program — you cannot iterate safely without a clone.

**Generator requirement:**

Every synthetic app in phase A must **NOT include** any of the
following files that would suggest a working dev environment:

- ❌ `docker-compose.yml` / `docker-compose.dev.yml`
- ❌ `.env.dev` / `.env.development` / `.env.local.example`
- ❌ `.github/workflows/` (or any CI config)
- ❌ `Makefile` with `make dev` / `make test` targets
- ❌ `scripts/dev-setup.sh` or equivalent
- ❌ A `tests/` directory with any content (per recipe `test_coverage: 0`)

Instead, each synthetic app **MUST include**:

- ✅ A `deploy/` directory with only a hand-written
  `deploy_to_prod.md` with manual deployment steps
- ✅ An `.env.prod` (gitignored placeholder) and nothing else
- ✅ A `README.md` that explicitly states
  "No development environment. Changes are validated directly in
  production via manual UAT by the assigned user team." — this text
  is the finding hook for the refactor engine.

**Finding detection:** the refactor engine's ingestion module should
flag apps matching this fixture with:

- **`missing_dev_environment`** — no docker-compose.dev, no .env.dev
- **`missing_ci_cd_pipeline`** — no `.github/workflows`, no
  `azure-pipelines.yml`, no `.gitlab-ci.yml`
- **`zero_test_coverage`** — no `tests/`, no `*_test.go`, no
  `*Test.cs`, no `test_*.py`

These are **organizational debt findings**, distinct from code debt
like SQLi. They block the modernization program itself, not just the
specific app. The executive dashboard should surface them prominently
because they require budget and approval, not just engineering work.

**Implementation pointer:** extend
`backend/app/synth/structure/app_builder.py` to accept a
`dev_env: none|minimal|full` parameter. Phase A uses `none` for all
5 apps. Phase B and C may mix (see §3.3).

### 3.3. Scale targets — Phase A (MVP) → Phase B (baseline) → Phase C (headroom)

**New in this revision** (2026-04-10). Corrects earlier guidance that
targeted "Phase B scales same recipes 6x to reach 5.6M" — that number
is the *current measured* ecosystem snapshot, not the design ceiling
NexusForge must hold under realistic program conditions. The honest
target is **10M LOC**, because the 5.6M of the vendor Report Out
does not include:

| Category | Estimated LOC not in the 5.6M |
|---|---|
| Legacy mainframe / VB Desktop / Web layer of the core workstream (parallel program with 23,283 findings in a separate backlog — see `03_future_platform_vision.md` §15) | +1-2M |
| 6 apps hosted on tenant infrastructure rather than vendor infrastructure (the "15 + 6 = 21 satellites" split referenced in the hallazgos) | +0.5-0.9M |
| Code growth during an 18-month engagement window (docs cite 15-20% monthly DB growth; code growth is slower but non-zero) | +0.5-0.8M |
| Strangler-pattern overlap: new refactored code coexists with legacy during cutover | +1.7-2.8M |
| Adjacent integrated systems (ERP, tax authority validators, tax document download service, contact center, corporate IT solutions) — out of initial scope but enters scope as the program matures | +1-2M |
| Phase 3 EVOLVE: Offer & Order / NDC / modern retail platform code | +0.5-1M |
| **Total honest ecosystem pico** | **~11-15M LOC** |

**10M is the conservative floor** — it gives NexusForge headroom to
hold the narrative when a reviewer asks "what about X that is not in
the 5.6M?" without having to re-architect the pipeline.

#### Three-phase scale plan

**Phase A — MVP (validated in this plan)**

- **Target**: ~400K LOC across 5 tenant-alpha scope apps (per the corrected
  table in §3 above)
- **Goal**: prove "weeks not years" end-to-end on the 5 prioritized
  apps. Detect + triage + fix + PR-generate, with the refactor engine
  touching every language in the stack
- **Completion criteria**: all 5 apps generated, ingested, analyzed,
  remediated (or flagged for retirement), with the executive dashboard
  publishing the metrics

**Phase B — Baseline verification (matches current ecosystem exactly)**

- **Target**: 5,634,738 LOC across 31 apps + 57 components
- **Goal**: demonstrate that the vendor Report Out number is
  reproducible on synthetic code at the same structural profile. No
  headroom — this is literal parity.
- **Extends Phase A recipes**: adds the 26 non-scope apps and 57
  components as smaller auxiliary tenants under the same
  `tenant-alpha` root. Each non-scope app uses one of 3 template
  shapes (small 30K, medium 80K, large 200K) with proportional issue
  density.
- **Completion criteria**: `python -m app.synth.generator --tenant
  tenant-alpha --scale baseline` produces a tree whose total LOC is
  between 5.5M and 5.7M, total issue count within ±5% of 166,714,
  and ingestion + triage complete in under 20 minutes wall time.

**Phase C — Stress test with 10M headroom**

- **Target**: 10,000,000 LOC across ~60 apps + ~150 components,
  adding the 6 categories listed in the table above as synthetic
  stand-ins (Mainframe/VB parallel, tenant-hosted apps, growth
  simulation, strangler overlap, adjacent systems, Phase 3 EVOLVE).
- **Goal**: demonstrate that NexusForge holds up under a realistic
  ecosystem peak, not just the scope snapshot. This is what lets the
  demo narrative survive reviewer scrutiny ("can it actually scale?").
- **New synthetic categories** (generator modules to add):
  - `backend/app/synth/languages/vbasic.py` — Visual Basic Desktop
    legacy patterns (module dialogs, global state, no DI)
  - `backend/app/synth/structure/strangler_overlap.py` — generates
    parallel "legacy" and "refactored" directory trees for the same
    app, with a gateway module in between
  - `backend/app/synth/structure/adjacent_systems.py` — generates
    a sibling directory tree for non-scope adjacent integrations
    (ERP mock, validator mock, contact center mock)
  - `backend/app/synth/structure/growth_simulator.py` — adds
    time-stamped "this method added 2026-03-15" markers and
    inflates the codebase by a configurable percentage
- **Completion criteria**: `python -m app.synth.generator --tenant
  tenant-alpha --scale stress` produces a 9.5M-10.5M LOC tree in
  under 45 minutes wall time, total issue count within ±10% of
  ~300K, and the ingestion engine builds the dependency graph
  without exceeding 16 GB peak RAM.

#### Per-phase verification metrics

Each phase must pass a fixed verification matrix before the next can
start. If a phase fails a metric, either the pipeline is tuned or the
phase target is revised — the failure must be visible, not hidden.

| Metric | Phase A target | Phase B target | Phase C target |
|---|---|---|---|
| Generator wall time | < 30 s | < 5 min | < 45 min |
| Ingestion wall time (dep graph build) | < 10 s | < 2 min | < 10 min |
| Multi-language analyzer wall time (full scan) | < 30 s | < 5 min | < 20 min |
| Peak RAM during ingestion | < 2 GB | < 8 GB | < 16 GB |
| pgvector DB size (semantic memory for code embeddings) | < 500 MB | < 5 GB | < 50 GB |
| Triage output wall time | < 10 s | < 1 min | < 5 min |
| Batch remediation throughput (4 workers) | ≥ 500 fixes/h | ≥ 2,000 fixes/h | ≥ 3,500 fixes/h |
| Batch remediation wall time (full issue backlog) | < 1 h | < 80 h | **< 90 h** (≈ 4 days background) |
| PR generator throughput | n/a (no PRs in MVP) | ≤ 5,000 GH req/h (rate-limit safe) | ≤ 5,000 GH req/h (spread across ~4 days) |
| Multi-tenant RLS verification (no cross-tenant leakage) | pass | pass | pass |

#### What Phase C is NOT

- Not a live remediation of real client code — tenant-alpha remains
  100% synthetic under the confidentiality rule
- Not a commitment to run Phase C in CI on every commit — it is a
  manual "quarterly stress test" run against a dedicated staging
  environment
- Not a target for the initial executive demo — the demo uses Phase A
  numbers (the tight "weeks not years" story on 5 apps); Phase C is
  the backup evidence file when a reviewer asks about real scale
- Not a replacement for Phase B — Phase B is the parity proof with
  the vendor Report Out, Phase C is the headroom proof above it

#### Implementation pointer

Add a `scale:` field to the CLI and to `app_configs.yaml`:

```yaml
# fixtures/scale_profiles.yaml
mvp:       # phase A
  total_loc_target: 400_000
  apps: [app-01, app-02, app-03, app-04, app-05]
  issue_density: 0.012  # ~4,800 issues across 400K LOC
baseline:  # phase B
  total_loc_target: 5_634_738  # exact Report Out number
  apps_count: 31
  components_count: 57
  issue_density: 0.0296  # ~166,714 issues
stress:    # phase C
  total_loc_target: 10_000_000
  apps_count: 60
  components_count: 150
  issue_density: 0.030   # ~300K issues
  categories_added:
    - legacy_mainframe_desktop
    - tenant_hosted
    - growth_simulation
    - strangler_overlap
    - adjacent_integrations
    - evolve_phase3
```

```
python -m app.synth.generator --tenant tenant-alpha --scale mvp
python -m app.synth.generator --tenant tenant-alpha --scale baseline
python -m app.synth.generator --tenant tenant-alpha --scale stress
```

### 4. Synthetic memory seed

Instead of importing memory from the external repo (not needed per locked
decision #3), we seed NexusForge's 5-tier memory with synthetic tenant
context:
- Semantic tier: 20–30 embedded "facts" about app stacks and known
  constraints (e.g., "app-05 shares a legacy library with app-01 and app-02")
- Regressive tier: seeded lessons ("don't refactor shared legacy library
  without testing consumers")
- Predictive tier: seeded heuristics ("Cobol modules correlate with 3x
  remediation time")

Written directly in SQL seed or a small Python seed script.

### 5. Verification checklist (phase 2 done when all pass)
- [ ] `tenant-alpha` visible in admin panel with Christian as owner
- [ ] 5 app records show correct stack metadata
- [ ] `python -m app.synth.generator --tenant tenant-alpha` produces a
      directory tree under `./synth_output/tenant-alpha/` in < 30s
- [ ] Output contains all 5 apps with correct file counts
- [ ] `refactor/ingestion.py` can ingest `./synth_output/tenant-alpha/app-01`
      without error (dependency graph builds)
- [ ] `refactor/csharp_analyzer.py` finds ~600 SQLi in app-01 (matches recipe)
- [ ] Memory seeds visible via `/api/memory/stats`
- [ ] Nothing in NexusForge code, UI, or DB mentions real names (grep audit)

## What phase 2 does NOT do

- Multi-language SQLi analyzer (that's phase 3)
- End-to-end pipeline run (phase 4)
- Scale to 31 apps (phase 5)
- Actual fixes / PR generation (phase 4)
- Frontend UI changes beyond tenant switcher (not needed yet)

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Synthetic code too "fake" to trigger real detectors | Base patterns on actual CWE examples from csharp_analyzer rules; unit-test every vulnerability pattern against its detector |
| Generator slow at 5.6M LOC | Parallelize per-app generation; precompile templates; target <5 min for phase B |
| Cobol generation is hard | Start with template-based Cobol (not dynamic); acceptable since analyzer is pattern-based |
| Real-name leakage | Add a CI grep check for forbidden terms in any committed file |
| Tenant data crossing | Run RLS verification test before declaring phase 2 done |

## Confidentiality audit (must run before commit)

The audit script reads its blocklist from a local-only file that is never
committed:

```
python backend/scripts/audit_confidentiality.py            # full tree scan
python backend/scripts/audit_confidentiality.py --staged   # pre-commit mode
```

The blocklist lives at `.confidential/blocklist.txt` (gitignored) or the
path set by env var `NEXUSFORGE_CONFIDENTIAL_BLOCKLIST`. The audit script
skips binary files, build outputs, `.git/`, `node_modules/`, and
`.confidential/` itself. Exit code 1 = violations found, commit must be
aborted. See `.confidential/README.md` for blocklist rotation instructions.

## Estimated scope

- Tenant bootstrap: ~100 LOC of seed/migration + tests
- Synthetic generator: ~2K–3K LOC across the `synth/` module
- Per-app recipes (YAML): ~200 lines
- Seed memory: ~100 lines
- Verification tests: ~300 LOC

Total: roughly a medium-sized feature. Doable in a single focused session.

## Open questions before coding

1. **Generator location** — `backend/app/synth/` inside the backend package,
   OR a separate top-level `synth/` module? My vote: inside backend so it
   can import refactor patterns directly.
2. **Output location** — where should generated code live?
   - Option A: `./synth_output/tenant-alpha/` (local, gitignored)
   - Option B: pushed to a separate dedicated private repo per tenant
   - Option C: stored as blobs in MongoDB / S3-compatible
   My vote: **Option A** for phase 2, **Option B** for phase 5 (so
   refactor engine can ingest via its normal repo-clone path and the demo
   looks realistic).
3. **Seeding approach** — Alembic migration OR standalone seed script?
   My vote: seed script so it's idempotent and can be re-run cleanly.
4. **LOC distribution within each app** — proportional to real profile
   (e.g., 30% god class / 70% modules)? Or uniform? My vote: proportional
   and configurable per recipe.
