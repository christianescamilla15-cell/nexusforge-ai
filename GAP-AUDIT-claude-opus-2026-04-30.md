# NexusForge gap audit — Claude Opus 4.7 — 2026-04-30

> **Triangulation note**: this is one of three independent audits.
> Codex and another Claude session will produce parallel reports.
> Only act on gaps that appear in **≥ 2 of the 3** audits independently.
> Single-audit findings are likely model artifacts, not real gaps.

## Methodology

- **Endpoint registration audit**: Parsed `backend/app/main.py` to identify which route modules are imported and registered via `app.include_router()`. Cross-referenced against all 38 route files in `backend/app/routes/`.
- **Frontend↔backend wiring**: Searched frontend for API calls (grep `/api/*`) and validated against backend routes; checked route files for existence of expected endpoints claimed in CLAUDE.md.
- **Half-finished features**: Searched for `TODO`, `FIXME`, `NotImplementedError`, and `pass` statements in backend routes; examined context to separate real gaps from intentional markers.
- **Test coverage**: Enumerated test files in `backend/tests/` and compared against route files; found 56 test files vs. 38 route modules; focused on missing coverage for high-traffic routes.
- **Feature flags**: Scanned `render.yaml` for `ENABLE_*` flags; found only `ENABLE_REFRESH_TOKENS=false` (known deferral documented in CLAUDE.md).
- **Stub modules**: Identified files <100 lines with minimal endpoints; none were actual stubs (smallest route file is `plugins.py` at 16 lines, which exports a single working endpoint).
- **Skipped**: Security hardening work (last 30 commits all security-focused), Pydantic v2 deprecations, test coverage percentages, coding style.

## Post-audit validation by Claude (before publishing)

Spot-checks performed against the agent's output to drop hallucinations:

- **Gap 1 (4 unregistered routes)** — verified by grepping `main.py` for `portfolio_copilot|orchestrator|evaluation|executions_db`: zero matches. Files exist on disk: confirmed via `ls backend/app/routes/`. **Solid.**
- **Gap 2 (meta.py unregistered)** — verified same way. `meta.py` exists with `prefix="/api/meta"` defined inside the router; not imported in main.py. **Solid.**
- **Gap 4 (Portfolio Copilot frontend↔backend mismatch)** — verified via grep of `frontend/src/features/chat/`: `ChatKnowledgeBase.js:483` defines `portfolio_copilot` agent; `chatEngine.js` references it in 3 places. Backend route is unreachable per Gap 1. **Solid.**
- **Gap 9 (recent Fernet rotation endpoints)** — agent rated 70% confidence. **CORRECTION: this is closed.** Today's commit `94eaf29` shipped `POST /admin/security/fernet-rotation/global` + `/tenant`. The agent didn't have visibility into the most recent commit. **Drop this gap.**
- **Gap 10 (refresh-tokens flag tracking)** — agent's framing was off; the deferral is intentional and operational, not a gap. Kept in the list but marked as low-priority informational.
- **Gap 3 + Gap 7 (test coverage)** — overlapping. Treat as one finding.

The remaining gaps below reflect those corrections.

## Gaps found

### Gap 1: Four production route modules are defined but never registered
- **Category**: api / operational
- **Evidence**:
  - `backend/app/routes/portfolio_copilot.py` (83 lines) — defines `@router.post("/run")`, `@router.get("/examples")`, `@router.get("/health")` at prefix `/portfolio-copilot`. NOT imported or registered in main.py.
  - `backend/app/routes/orchestrator.py` (102 lines) — defines `/orchestrator/snapshot`, `/orchestrator/agent/{agent_id}`, `/orchestrator/feed`, etc. NOT in main.py.
  - `backend/app/routes/evaluation.py` (284 lines) — defines full CRUD for evaluation scenarios and runs (`/evaluation/scenarios`, `/evaluation/runs`, etc.). NOT in main.py.
  - `backend/app/routes/executions_db.py` (295 lines) — defines DB-backed execution query endpoints (`/executions-db`, `/executions-db/{id}`, `/executions-db/timeline/{id}`, etc.). NOT in main.py.
- **Frontend impact**: `portfolio_copilot` is explicitly documented in frontend ChatKnowledgeBase.js (references `/api/portfolio-copilot/run`). Frontend will 404 if a user invokes the agent.
- **Impact**: high (substantial production modules; portfolio_copilot is user-facing; evaluation and executions_db provide persistence that survives server restarts)
- **Effort**: S (add 4 import lines + 4 `include_router()` lines in main.py)
- **Recommendation**: Import all four routers in main.py and register them with appropriate prefixes. Run `pytest backend/tests/` to ensure no surprise import-time side effects.

### Gap 2: Meta-orchestration API routes are defined but not registered
- **Category**: api / operational
- **Evidence**: `backend/app/routes/meta.py` (256 lines) — defines `/api/meta/pipeline`, `/api/meta/reason`, `/api/meta/generate-spec`, `/api/meta/predict-features`, `/api/meta/optimize-flow`, `/api/meta/sdk/*` routes. Uses `prefix="/api/meta"` (line 12). Not imported or registered in main.py. Exports `ArchitectureReasoner`, `SpecGenerator`, `FeaturePredictor`, `FlowOptimizer` — non-trivial agents.
- **Impact**: medium (internal/dev tools surface; not immediate user-facing, but blocks SDK integration if needed)
- **Effort**: S (one import + one include_router line)
- **Recommendation**: Register if these agents are intended for production. If they're not — delete the file. The middle ground (file exists but unreachable) is the worst state.

### Gap 3: Portfolio Copilot route is documented in frontend but unreachable
- **Category**: feature / api mismatch
- **Evidence**:
  - `frontend/src/features/chat/ChatKnowledgeBase.js:483` defines `portfolio_copilot` as a user-facing agent.
  - `chatEngine.js` lines 156-158 reference it as a routing target from `enterprise_ops` and `document_intelligence`.
  - Backend implements `portfolio_copilot.py` with `POST /run`, `GET /examples`, `GET /health`. But unreachable per Gap 1.
- **Impact**: high (documented user-facing feature with zero working surface)
- **Effort**: S (resolved by Gap 1's fix)
- **Recommendation**: Folded into Gap 1.

### Gap 4: Evaluation scenarios and runs are implemented but unreachable and untested
- **Category**: feature / operational
- **Evidence**:
  - `backend/app/routes/evaluation.py` (284 lines) defines full scenario + run CRUD.
  - Uses PostgreSQL (`pool.acquire()` + asyncpg queries to `evaluation_scenarios` and `evaluation_runs` tables).
  - Implements RUN endpoints that trigger evaluations and record results — core feature for model-quality testing.
  - Zero unit tests; no integration test reference in `test_full_system.py`.
- **Impact**: medium (limits ability to programmatically test model performance; persistence layer assumed but never exercised)
- **Effort**: M (register router + write `tests/test_evaluation.py` with scenario CRUD + run trigger tests; verify migrations include `evaluation_scenarios` + `evaluation_runs` tables)
- **Recommendation**: Confirm migrations exist for the two tables. If they do, Gap 1's fix + a test file is enough. If not, add migration first.

### Gap 5: Executions-DB route provides persistence but is unreachable and lacks tests
- **Category**: feature / operational
- **Evidence**:
  - `backend/app/routes/executions_db.py` (295 lines) defines `/executions-db/*` endpoints querying PostgreSQL `workflow_runs` table.
  - Complements in-memory `/api/executions/*` routes with persistent query endpoints that survive server restarts.
  - CLAUDE.md mentions `/api/executions/*` but NOT `/api/executions-db/*` (doc gap).
  - Not registered in main.py; no test coverage.
- **Impact**: medium (operational tooling for execution history queries that survive restart; 404 if frontend tries to call)
- **Effort**: S (register) + M (write `tests/test_executions_db.py`)
- **Recommendation**: Register + test. Update CLAUDE.md to list both `/api/executions/*` (in-memory) and `/api/executions-db/*` (persistent).

### Gap 6: Major routes lack dedicated unit test files
- **Category**: coverage
- **Evidence**: Routes without corresponding `tests/test_*.py`: `refactor.py` (~1800 lines), `executions.py` (~500 lines), `workflows.py` (~600 lines), `automations.py` (~700 lines), `agents.py` (~600 lines). `test_full_system.py` (17 functional tests) covers end-to-end but does NOT substitute for unit tests on endpoint contracts.
- **Impact**: medium (CI gating gap — schema changes can ship without breaking tests; risk of silent contract regressions)
- **Effort**: L (5-10h to write ~200 test cases for the 5 largest routes)
- **Recommendation**: Establish coverage baseline: `pytest backend/tests/ --cov=app/routes --cov-report=term`. Prioritize `refactor`, `executions`, `workflows`, `automations`, `agents`. Don't aim for 100%; aim for happy-path + 2-3 error cases per route.

### Gap 7: CLAUDE.md endpoint surface diverges from reality
- **Category**: doc
- **Evidence**: CLAUDE.md § "API Endpoints (active)" does NOT mention `/api/portfolio-copilot`, `/api/orchestrator`, `/api/evaluation`, `/api/executions-db`, or `/api/meta/*`. Three of these are substantial production-ready modules absent from the "active" list.
- **Impact**: low (mostly doc; but hurts onboarding and future audits)
- **Effort**: S (update CLAUDE.md after Gap 1+2 are fixed; one-line per route)
- **Recommendation**: Treat CLAUDE.md as authoritative — every route in the registered set should be listed; every listed route should be registered. Cleanup follows naturally from Gap 1+2 resolution.

### Gap 8: Refresh-token frontend interceptor work has no visible tracking
- **Category**: operational / informational
- **Evidence**: `render.yaml:38-39` sets `ENABLE_REFRESH_TOKENS=false`. CLAUDE.md documents this as deferral pending frontend interceptor. Backend supports refresh tokens fully (commit `ea6e217`). Pattern: a backend feature exists, is correct, and is gated off until frontend ships interceptor.
- **Impact**: low (known deferral; but visibility is poor — without an issue tracker entry this can rot)
- **Effort**: S (open issue or note)
- **Recommendation**: Either open a tracked issue for the frontend work or accept that this lives in CLAUDE.md only. Don't leave it floating in commit messages.

## Areas confirmed healthy

- **Frontend router coverage**: All 24 lazy-loaded pages in `App.jsx` resolve to existing components. No broken imports / 404 stubs.
- **CLAUDE.md most claims verified**: Most claimed active endpoints exist and are registered (the 5 in Gap 1+2 are the exceptions).
- **Backend dependency pins**: `anthropic==0.94.0`, `fastapi==0.115.0`, `pydantic>=2.10.0` are current. No stale pins identified.
- **Security hardening complete**: Last 30 commits security-focused. No obvious security TODOs or hardcoded secrets in route definitions. (This was the focus of the last 6 days; intentionally excluded from this audit.)
- **Integration test infrastructure working**: `test_full_system.py` runs 17 functional tests. Fixtures in `conftest.py` properly set up DB/Redis/auth.
- **Admin Fernet rotation operational tooling**: Closed today (commit `94eaf29`) — both global and per-tenant rotation reachable via `POST /admin/security/fernet-rotation/{global,tenant}`.

## Confidence notes

- **Gap 1 (4 unregistered routes): 100%.** Direct grep of main.py confirms. Files exist via ls.
- **Gap 2 (meta routes): 95%.** Same verification path. Small residual risk that meta is loaded dynamically elsewhere (would surface as feature 5 already-shipped); not investigated.
- **Gap 3 (Portfolio Copilot doc/code mismatch): 100%.** Frontend reference + backend file existence + main.py absence all confirmed.
- **Gap 4–5 (Evaluation, Executions-DB): 90%.** Files inspected, routes look well-formed, DB queries present. Confidence not 100% because the migrations for the implied tables weren't verified.
- **Gap 6 (test coverage): 85%.** High-traffic routes lack dedicated unit test files; some incidental coverage may exist via integration tests.
- **Gap 7 (CLAUDE.md drift): 100%.** Direct comparison of CLAUDE.md vs route listing.
- **Gap 8 (refresh-tokens): informational.** Known deferral, not a gap proper.

## Recommended triage order if all 3 audits agree

1. **Gap 1+3 first** (one fix closes both). 30 min: 4 import lines, 4 include_router lines, smoke test, ship. Closes the loudest user-facing breakage.
2. **Gap 4+5** (evaluation, executions_db). Verify migrations → register → write minimal tests.
3. **Gap 7** (CLAUDE.md cleanup). Falls out of Gap 1+2.
4. **Gap 6** (test coverage). Largest effort; only after the wiring is settled.
5. **Gap 2** (meta) — decide: register, or delete. Don't leave half-built.
6. **Gap 8** (refresh-tokens tracking) — just open an issue.
