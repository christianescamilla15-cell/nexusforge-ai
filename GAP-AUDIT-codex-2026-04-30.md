# NexusForge gap audit - Codex - 2026-04-30

> Independent non-security audit focused on feature, operational, and coverage gaps.
> Security hardening items, Pydantic deprecations, style issues, coverage percentages,
> and dead imports were intentionally excluded.

## Methodology

- **Route registration audit**: Parsed `backend/app/main.py` router imports and
  `app.include_router(...)` calls, then cross-checked all 37 route modules under
  `backend/app/routes/`. Static result: 32 registered, 5 unregistered.
- **Frontend/backend contract audit**: Grepped `frontend/src` for `fetchAPI(...)`,
  direct `fetch(...)`, and WebSocket construction, then compared endpoint paths
  and request payload shapes against backend route decorators and Pydantic/Form
  inputs.
- **Documentation drift audit**: Compared CLAUDE.md, README, frontend API docs,
  deployment docs, and route docstrings against registered routes. Security-only
  drift such as `/api/mythos/key` was noted but not counted as a gap.
- **Half-finished feature scan**: Searched non-security code for `TODO`,
  `NotImplementedError`, "not implemented", placeholders, and stubs. I filtered
  out deliberate synthetic tenant stubs and generated migration skeletons unless
  they undercut a claimed platform feature.
- **Coverage audit**: Looked for route-level tests for high-traffic workflow,
  execution, automation, result, and run-history endpoints. I focused on whether
  endpoint contracts are tested, not on percentage coverage.
- **Operational task audit**: Searched for `render exec` and direct production
  scripts. Non-security `render exec` requirements were not found; the remaining
  references are key-rotation/Mythos security runbook items, with Fernet rotation
  already exposed through admin endpoints.

## Gaps found

### Gap 1: Portfolio Copilot is advertised but its backend route is unreachable
- **Category**: api / feature mismatch
- **Evidence**:
  - `backend/app/routes/portfolio_copilot.py:12` defines prefix `/portfolio-copilot`.
  - `backend/app/routes/portfolio_copilot.py:14`, `:71`, `:76` define `/run`,
    `/examples`, and `/health`.
  - `frontend/src/features/chat/ChatKnowledgeBase.js:486` documents
    `POST /api/portfolio-copilot/run`; `README.md:114` advertises the same API.
  - `backend/app/main.py:248-292` registers production routers, but there is no
    `portfolio_copilot` import or `include_router`.
- **Impact**: High. A user-facing feature described in the chat knowledge base
  and README returns 404 in the deployed FastAPI app.
- **Effort**: S.
- **Recommendation**: Register the router, then add a smoke test for
  `/api/portfolio-copilot/health` and one contract test for `/run`.

### Gap 2: Evaluation scenario/run API exists with migrations but is not registered
- **Category**: api / operational
- **Evidence**:
  - `backend/app/routes/evaluation.py:13` defines prefix `/evaluation`.
  - `backend/app/routes/evaluation.py:22`, `:62`, `:101`, `:221`, `:245`
    define scenario CRUD, run execution, and result endpoints.
  - `backend/app/db/migrations/001_observability.sql:61` creates
    `evaluation_scenarios`; `:72` creates `evaluation_runs`.
  - `backend/app/main.py:248-292` never includes `evaluation.py`.
- **Impact**: Medium-high. The "Evaluation Harness" feature is described in
  `frontend/src/features/chat/ChatKnowledgeBase.js:518`, but its actual API
  cannot be reached.
- **Effort**: S to register, M to add scenario/run tests.
- **Recommendation**: Register `/api/evaluation/*` if this is production
  surface; otherwise remove the route and update the Evaluation Harness copy.

### Gap 3: Persistent execution detail API is unregistered
- **Category**: api / operations
- **Evidence**:
  - `backend/app/routes/executions_db.py:15` defines prefix `/executions-db`.
  - `backend/app/routes/executions_db.py:26`, `:72`, `:100`, `:128`, `:270`
    expose DB-backed run list, steps, events, timeline, and checkpoints.
  - The registered `/api/runs/{run_id}/steps` and `/events` path in
    `backend/app/routes/workflow_runs.py:284-292` reads the in-memory collector,
    while `executions_db.py:77-88` reads `workflow_steps` from PostgreSQL.
  - `backend/app/main.py:248-292` never includes `executions_db.py`.
- **Impact**: Medium. Operators have no registered API for persisted execution
  timelines after process restart, despite the tables and query code existing.
- **Effort**: S to register, M to test ownership and timeline responses.
- **Recommendation**: Either register `/api/executions-db/*` or fold its
  DB-backed behavior into `/api/runs/*` and delete the duplicate route module.

### Gap 4: Meta-orchestration routes are tested in isolation but absent from main
- **Category**: api / dev-tools
- **Evidence**:
  - `backend/app/routes/meta.py:12` defines `APIRouter(prefix="/api/meta")`.
  - `backend/app/routes/meta.py:50`, `:93`, `:117`, `:151`, `:171`, `:190`
    define pipeline, reasoning, spec generation, feature prediction, flow
    optimization, and SDK bridge endpoints.
  - `backend/tests/test_meta.py:196` only imports `app.routes.meta.router` and
    asserts standalone route paths; it does not verify registration in
    `app.main`.
  - `backend/app/main.py:248-292` never includes `meta.py`.
- **Impact**: Medium. The module is non-trivial and test-visible, but clients
  cannot reach it.
- **Effort**: S, with care.
- **Recommendation**: If registering it, include `meta_router` without an extra
  `/api` prefix because `meta.py:12` already embeds `/api/meta`; otherwise the
  route would become `/api/api/meta/*`.

### Gap 5: Orchestrator memory-control API is unregistered
- **Category**: api / operational tooling
- **Evidence**:
  - `backend/app/routes/orchestrator.py:8` defines prefix `/orchestrator`.
  - `backend/app/routes/orchestrator.py:32`, `:40`, `:48`, `:56`, `:66`,
    `:81`, `:90` expose snapshot, agent memory, feed/log, context injection,
    broadcast, and session documentation endpoints.
  - `backend/app/main.py:248-292` never includes `orchestrator.py`.
- **Impact**: Medium. The code claims an operator/Claude-facing control plane
  for agent memory, but it has no HTTP surface.
- **Effort**: S to register, M if auth/role boundaries need to be defined.
- **Recommendation**: Decide whether this is admin-only production tooling or
  dev-only. Register behind admin auth or remove it.

### Gap 6: Enterprise Ops tab sends the wrong request and reads the wrong health key
- **Category**: frontend/backend contract
- **Evidence**:
  - `frontend/src/features/intelligence/IntelligenceHubPage.jsx:60` calls
    `/enterprise-ops/process`.
  - `frontend/src/features/intelligence/IntelligenceHubPage.jsx:62` sends
    `{ text, language }`.
  - `backend/app/use_cases/enterprise_ops/schemas.py:5-9` requires
    `OperationsRequest.message`, not `text`.
  - `backend/app/routes/enterprise_ops.py:25` is the registered route.
  - The frontend reads `health.supported_intents` at
    `IntelligenceHubPage.jsx:77-79`, while the backend returns
    `intents_supported` at `backend/app/routes/enterprise_ops.py:96`.
- **Impact**: High for the Intelligence Hub. The run action will 422, and the
  health UI silently omits supported intents.
- **Effort**: S.
- **Recommendation**: Change the frontend payload to `{ message: text, language }`
  and read `intents_supported`, or add backend aliases with tests.

### Gap 7: Document Intelligence tab sends `text`, but the backend requires `content`
- **Category**: frontend/backend contract
- **Evidence**:
  - `frontend/src/features/intelligence/IntelligenceHubPage.jsx:153` calls
    `/document-intelligence/run`.
  - `frontend/src/features/intelligence/IntelligenceHubPage.jsx:155` sends
    `{ text, language }`.
  - `backend/app/use_cases/document_intelligence/schemas.py:4-7` requires
    `DocumentIntelligenceInput.content`.
  - `backend/app/routes/document_intelligence.py:14` exposes the JSON body route.
  - `frontend/src/features/chat/ChatKnowledgeBase.js:479` says the API uses
    multipart form data, which also diverges from the registered route.
- **Impact**: High for the Intelligence Hub tab; request validation fails before
  the workflow starts.
- **Effort**: S.
- **Recommendation**: Send `{ content: text, language, filename: "text_input" }`
  from the tab and correct the knowledge-base API description.

### Gap 8: Intelligence Hub Analyze tab posts JSON to a Form endpoint
- **Category**: frontend/backend contract
- **Evidence**:
  - `frontend/src/features/intelligence/IntelligenceHubPage.jsx:242` calls
    `/analyze/text`.
  - `frontend/src/features/intelligence/IntelligenceHubPage.jsx:244` sends
    JSON `{ text, language }`.
  - `backend/app/routes/analyze.py:370` defines `POST /analyze/text`.
  - `backend/app/routes/analyze.py:372-374` requires form fields
    `content` and `language`.
  - The older Analyze page uses direct `FormData` for the same route in
    `frontend/src/features/analyze/AnalyzePage.jsx:102`, so the mismatch is
    localized to the Intelligence Hub.
- **Impact**: Medium-high. One of the three Intelligence Hub tabs cannot submit.
- **Effort**: S.
- **Recommendation**: Use `FormData` with `content`, or add a JSON-compatible
  endpoint and point the tab at that contract.

### Gap 9: Chat-first preview opens a WebSocket path that does not exist
- **Category**: frontend/backend wiring
- **Evidence**:
  - `frontend/src/features/chat-first/hooks/usePreviewEvents.jsx:27` opens
    `${apiUrl}/ws/${runId}`; with the default API URL this becomes
    `/api/ws/{runId}`.
  - `backend/app/routes/executions.py:340` defines only
    `@router.websocket("/ws/{run_id}")`, and `backend/app/main.py:250`
    mounts that router at `/api/executions`.
  - `frontend/src/shared/hooks/useExecutionWS.js:32` shows the correct pattern:
    replace `/api` with `/api/executions` before appending `/ws/{runId}`.
- **Impact**: Medium. Chat-first live workflow previews will not receive step
  status updates.
- **Effort**: XS.
- **Recommendation**: Reuse `useExecutionWS` or build the same
  `/api/executions/ws/{runId}` URL in `usePreviewEvents`.

### Gap 10: `/api/v1` is documented as a full mirror but mounts only a subset
- **Category**: api versioning / operational
- **Evidence**:
  - `backend/app/main.py:297` says clients should migrate to `/api/v1/`.
  - `backend/app/main.py:309` says "Mount all existing routes under /api/v1/ as well".
  - `backend/app/main.py:310-312` mounts only auth, billing, API keys, wizard,
    results, analyze, automations, SDK, refactor, organizations, and admin.
  - Core v0 routers such as workflows, executions, agents, documents, swarms,
    integrations, feedback, drive pipeline, connectors, templates, rules,
    variables, audit log, metrics, and runs are registered at
    `backend/app/main.py:249-273` but not in the v1 mirror.
- **Impact**: Medium. A client following the stability guidance will hit 404s
  for core endpoints.
- **Effort**: S-M depending on whether v1 should be a true mirror.
- **Recommendation**: Either mount every intended router under v1 or change the
  comment/docs to say v1 is partial.

### Gap 11: Frontend API docs page links to disabled docs and lists the wrong API-key endpoint
- **Category**: docs / frontend operations
- **Evidence**:
  - `frontend/src/features/docs/ApiDocsPage.jsx:8` computes `/docs` from the
    API URL and `:35` links users to it.
  - `backend/app/main.py:154-158` disables `/docs`, `/redoc`, and
    `/openapi.json` when `settings.debug` is false.
  - `frontend/src/features/docs/ApiDocsPage.jsx:51` claims
    `POST /api/api-keys`.
  - `backend/app/auth/api_keys.py:123`, `:163`, `:195` expose
    `POST /api/api-keys/generate`, `GET /api/api-keys/`, and
    `DELETE /api/api-keys/{key_id}`; there is no root `POST`.
- **Impact**: Medium. The in-app documentation points production users at a 404
  and gives them a bad API-key creation route.
- **Effort**: S.
- **Recommendation**: Render a local endpoint reference in production and fix
  the API-key row to `/api/api-keys/generate`.

### Gap 12: Deployment readiness docs reference a nonexistent endpoint
- **Category**: operational docs
- **Evidence**:
  - `docs/DEPLOYMENT.md:459` documents `GET /api/health/ready`.
  - `backend/app/routes/health.py:13`, `:19`, `:32` define only `/ping`,
    `/version`, and `/health`.
- **Impact**: Medium if Render/Kubernetes probes are configured from the docs;
  readiness checks will fail with 404.
- **Effort**: S.
- **Recommendation**: Either add `/api/health/ready` with dependency checks or
  update the deployment docs to use `/api/health`.

### Gap 13: High-traffic workflow/execution routes lack route-level contract tests
- **Category**: coverage
- **Evidence**:
  - Frontend creation paths call `/wizard/generate`, `/workflows/`,
    `/automations/`, and `/executions/` from
    `frontend/src/features/chat-first/ChatPanel.jsx:148`, `:189`, `:224` and
    `frontend/src/features/workflows/WorkflowBuilderPage.jsx:466`, `:494`.
  - Dashboard/run-history views call `/runs/` and reliability health at
    `frontend/src/features/dashboard/DashboardPage.jsx:395-396`.
  - Route contracts live in `backend/app/routes/workflows.py:34-171`,
    `executions.py:35-340`, `automations.py:173-551`,
    `results.py:41-298`, and `workflow_runs.py:203-307`.
  - Existing HTTP-style tests are concentrated in auth/admin:
    `backend/tests/test_auth.py:52-57` builds a standalone auth app, and
    `backend/tests/test_admin_fernet_rotation.py:75-93` builds a standalone
    admin app. There are no dedicated `test_workflows.py`,
    `test_executions.py`, `test_automations.py`, `test_results.py`, or
    `test_workflow_runs.py` files in `backend/tests/`.
- **Impact**: High. Schema or auth regressions in the busiest product paths can
  ship without a failing endpoint test.
- **Effort**: L.
- **Recommendation**: Add a narrow contract suite: happy path plus auth/error
  cases for create/list/get/update/delete workflows, start/get/delete
  executions, run automations, create/list/delete results, and run-history
  reads.

### Gap 14: C# test generation emits placeholder tests that always pass
- **Category**: half-finished feature / coverage quality
- **Evidence**:
  - `backend/app/refactor/cicd_generator.py:276` emits
    `Assert.True(true); // TODO: implement real assertion`.
  - `backend/app/refactor/cicd_generator.py:290` emits another
    `Assert.True(true); // TODO: implement`.
  - `backend/app/refactor/cicd_generator.py:301` emits
    `// TODO: Wire up dependency injection / mocks`.
- **Impact**: Medium. The platform claims to generate xUnit/Jest/pytest tests,
  but C# generated tests can pass without exercising behavior.
- **Effort**: M.
- **Recommendation**: Either label these as scaffolds in the API response, or
  generate assertion templates from method signatures/return types and mark
  incomplete tests as skipped instead of passing.

### Gap 15: CLAUDE.md "active endpoints" list is materially stale
- **Category**: docs / operational onboarding
- **Evidence**:
  - `CLAUDE.md:60-70` presents an "API Endpoints (active)" list.
  - Registered non-security routers missing from that list include runs and
    metrics at `backend/app/main.py:260-261`, Enterprise Ops and Document
    Intelligence at `:262-263`, integrations/feedback/drive pipeline at
    `:264-266`, connectors/templates/rules/variables/audit log at `:269-273`,
    organizations/admin at `:285-288`, plus results at `:257` and demo at
    `:276`.
  - The same CLAUDE.md list does not mention the frontend-used
    `/api/analyze`, `/api/analyze/text`, or `/api/pipeline-runs` endpoints
    implemented in `backend/app/routes/analyze.py:221`, `:370`, `:499`.
- **Impact**: Medium. New work based on CLAUDE.md will miss active product
  surfaces and may repeat the route-registration drift above.
- **Effort**: S.
- **Recommendation**: Treat CLAUDE.md as an index generated from `main.py`:
  update it after route registration decisions, and keep security-only drift
  such as `/api/mythos/key` out of this non-security audit.

## Areas confirmed healthy

- **Most frontend endpoint paths exist**: Static extraction found one path-level
  miss (`/api/ws/{runId}`); the other frontend failures above are request/body
  contract mismatches, not missing routes.
- **Core route registration is mostly intact**: Workflows, executions, agents,
  documents, swarms, integrations, feedback, drive pipeline, analyze,
  automations, connectors, templates, rules, variables, audit log, demo, SDK,
  refactor, organizations, admin, and Mythos are registered in `main.py`.
- **Evaluation/execution persistence has schema support**: The unregistered
  evaluation and executions-db APIs are not blocked by missing migrations;
  `001_observability.sql` creates their underlying tables.
- **Operational `render exec` audit did not reveal non-security blockers**:
  Remaining `render exec` references are in key-rotation/Mythos security
  runbooks. Fernet global and per-tenant rotations already have admin HTTP
  endpoints in `backend/app/routes/admin.py:470` and `:507`.
- **Frontend route component imports look present**: The lazy imports in
  `frontend/src/App.jsx:18-43` resolve to files present in `frontend/src`.
- **Intentional synthetic stubs were not counted**: `NonScopeAppStub`,
  `DISCOVERY_PENDING.md`, and strangler migration skeleton outputs appear
  deliberate and are documented as generated scaffolding.

## Confidence notes

- **Gaps 1-5: high confidence.** Static route import parsing found exactly five
  unregistered route modules: `evaluation.py`, `executions_db.py`, `meta.py`,
  `orchestrator.py`, and `portfolio_copilot.py`.
- **Gaps 6-9: high confidence.** These are direct line-by-line frontend/backend
  contract mismatches. They should reproduce as 422s or missing WebSocket
  updates unless another proxy rewrites payloads/paths.
- **Gap 10: high confidence.** The v1 mirror list is explicit in `main.py` and
  omits multiple core routers.
- **Gaps 11-12: high confidence.** These are documentation/UI claims compared
  with actual route decorators and FastAPI docs configuration.
- **Gap 13: medium-high confidence.** I verified the absence of dedicated
  route-level test files and saw HTTP TestClient usage concentrated in auth and
  admin tests. Some indirect module coverage exists in `backend/test_full_system.py`,
  but it does not exercise HTTP contracts for the high-traffic routes.
- **Gap 14: medium confidence.** The placeholders are definitely emitted; the
  only judgment call is whether they are acceptable scaffolding or should be
  treated as incomplete generated tests.
- **Gap 15: high confidence.** Direct comparison of CLAUDE.md to `main.py`
  shows multiple active non-security routers omitted from the advertised
  endpoint surface.
- **Security exclusions**: I did not count `/api/mythos/key` CLAUDE.md drift,
  Fernet rotation runbooks, or other security hardening leftovers because the
  requested scope was explicitly non-security.
