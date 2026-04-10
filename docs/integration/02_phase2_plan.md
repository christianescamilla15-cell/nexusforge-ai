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

| Codename | LOC target | Primary lang | DB | Key injected issues |
|---|---|---|---|---|
| app-01 | 180K | C# ASP.NET | Aurora MySQL | ~600 SQLi, hardcoded conn strings, no tests, god class |
| app-02 | 150K | C# .NET | SQL Server | ~450 SQLi, MD5 hashing, 97% no FK, no CI/CD |
| app-03 | 80K | Python (Playwright) | SQLite + DB2 | ~200 SQLi, hardcoded JWT secret, fragile selectors, no tests |
| app-04 | 120K | VB.NET + C# | SQL Server | ~400 SQLi, obsolete SHA1, PII columns unencrypted |
| app-05 | 370K | C# + Cobol + Java | SQL Server + DB2 + MySQL + Oracle | ~1,350 SQLi, 8 langs touched, god class shared with 2 others, weak crypto, no FK |

**Total phase A:** 900K LOC, ~3,000 SQL injections, 150K+ issues, matches
real profile at ~1/6 scale. Phase B scales same recipes 6x to reach 5.6M.

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
