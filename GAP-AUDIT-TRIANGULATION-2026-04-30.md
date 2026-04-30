# Gap-audit triangulation — 2026-04-30

> Synthesis of 3 independent audits. Source files:
> - `GAP-AUDIT-claude-opus-2026-04-30.md` (this Claude session — Opus 4.7 at master HEAD `94eaf29`)
> - `GAP-AUDIT-codex-2026-04-30.md` (Codex at base commit `ec79bd2`, ~28 commits behind master — security work missing from its view but structural gaps still valid since none of those files were touched after `ec79bd2`)
> - Third Claude session — file `GAP-AUDIT-claude-opus-4-7-2026-04-30.md` was reported as written but is NOT on disk in the project root. Triangulation here uses the headlines pasted by Christian.

## Methodology adjustment

The original rule "fix gaps in ≥ 2 of 3 audits, discard the rest" is wrong when applied mechanically. Each model samples different parts of the codebase, so even a real bug can land in only one report. The corrected rule:

- **3/3** → fix without further validation
- **2/3** → fix
- **1/3 with mechanically verifiable evidence** (specific file:line + grep-checkable claim) → **VERIFY by inspection, then fix if real**
- **1/3 with vague evidence or judgment-call framing** → discard or downgrade to "needs review"

I performed inspection on the 1/3 high-evidence claims below and promoted those that survived.

## Tier 1 — Triple-confirmed (3/3) — fix without further validation

### T1.1 — Five route modules defined but never registered in main.py

| Module | Frontend impact |
|---|---|
| `portfolio_copilot.py` | **High** — advertised in README.md:114 + ChatKnowledgeBase.js:486; user-facing 404 |
| `evaluation.py` | **Med-high** — Evaluation Harness in ChatKnowledgeBase.js:518; migrations exist (`001_observability.sql:61,72`) |
| `executions_db.py` | Med — DB-backed execution timeline, no frontend caller verified |
| `meta.py` | Med — has `prefix="/api/meta"` already; if registered, mount WITHOUT extra `/api` prefix |
| `orchestrator.py` | Med — agent memory control plane, no caller verified |

**Effort**: S (4-5 import lines + include_router calls). **Trap to avoid**: meta.py already has `/api/meta` baked in — register without an extra prefix or you get `/api/api/meta/*`.

### T1.2 — High-traffic routes lack contract tests

Routes without dedicated `tests/test_*.py`: `refactor.py` (~1800 LOC), `executions.py` (~500), `workflows.py` (~600), `automations.py` (~700), `agents.py` (~600), `results.py`, `workflow_runs.py`. `test_full_system.py` covers 17 functional flows but does not exercise endpoint contracts (schema validation, auth, error paths).

**Effort**: L (5-10h for happy-path + 2-3 error cases per route). **Triage**: don't do this until T1.1 + T2.1 are fixed — wiring fixes will change the test surface.

## Tier 2 — Double-confirmed (2/3) — fix

### T2.1 — `/api/v1/` mirror is partial despite the comment claiming full parity

`backend/app/main.py:297-312` says clients should migrate to `/api/v1/` and the comment claims "Mount all existing routes under /api/v1/ as well", but only ~10 of ~30 routers are mounted there. Workflows, executions, agents, documents, swarms, integrations, feedback, drive pipeline, connectors, templates, rules, variables, audit log, metrics, runs are NOT mirrored.

**Effort**: S–M (decision: full mirror, or fix the comment to say "partial — the following endpoints are stable under v1").
**Source**: codex Gap 10 + third Claude headline 3.

### T2.2 — CLAUDE.md endpoint surface is materially stale

CLAUDE.md § "API Endpoints (active)" omits `runs`, `metrics`, `enterprise_ops`, `document_intelligence`, `integrations`, `feedback`, `drive_pipeline`, `connectors`, `templates`, `rules`, `variables`, `audit`, `organizations`, `analyze/text`, `pipeline-runs`, `demo`, `results`, `health`, plus the 5 unregistered routes from T1.1.

**Effort**: S — but only meaningful AFTER T1.1 ships, so the list reflects the actual registered set.
**Source**: this Claude (Gap 7) + codex Gap 15.

## Tier 3 — Single-source, evidence verified by inspection — fix

These appeared in only one audit but I checked the evidence directly. Each is a real bug.

### T3.1 — Two `/audit` routers shadow each other → main audit page silently empty + SQL bug

**Verified**:
- `main.py:20` `from app.routes.audit import router as audit_log_router` (registered line 273 with `prefix="/api"`)
- `main.py:232` `from app.auth.audit import router as audit_routes` (registered line 238 with `prefix="/api"`)
- Both mount under `/api`. FastAPI route lookup is order-dependent — whichever is registered first wins for shared paths.
- `auth/audit.py:67-69` has a SQL bug: `SELECT ... FROM audit_log WHERE user_id = $1::uuid ... LIMIT $1` — the same `$1` is reused for both `user_id` and `LIMIT`. The query binds `(token_data["sub"], limit)` — Postgres uses `$1` for `user_id` and `$2` for the unused second arg. The `LIMIT $1` resolves to a UUID-like value → SQL error or 0 rows.
- Two divergent tables exist: `audit_log` (singular, in `010_audit_log.sql` AND duplicated in `013_api_keys_audit_custom_agents.sql`) vs `audit_logs` (plural, in `022_variables_logs.sql`) — different schemas, different row counts, drift unbounded.

**Impact**: High. Audit page silently empty in production. Two duplicate `audit_log` migrations also a foot-gun.
**Effort**: M. Pick one router + one table, delete the other, fix the SQL bug, write a regression test.
**Source**: third Claude headline 2 only — but evidence reproduced 1:1.

### T3.2 — Cron parser ignores DOW/DOM/month — `30 9 * * 1-5` fires weekends

**Verified** at `backend/app/routes/automations.py:609`:
```python
def _next_run(cron: str) -> datetime:
    """Very simple cron: only handles */N minute patterns and fixed hour/day."""
```
The function only reads `parts[0]` (minute) and `parts[1]` (hour). `parts[2]` (DOM), `parts[3]` (month), `parts[4]` (DOW) are ignored entirely. The docstring admits it.

**Impact**: Med-high if any user schedules with DOW restrictions; the platform claims cron support but silently broadens schedules.
**Effort**: S — swap to `croniter` (already a common Python lib) or add DOW handling. Either path needs tests for the failure mode.
**Source**: third Claude headline 6 only — verified.

### T3.3 — Intelligence Hub: 3 frontend↔backend payload mismatches → 422 in production

**Verified**:
- `IntelligenceHubPage.jsx:60` POSTs `{ text, language }` to `/enterprise-ops/process`. Backend `OperationsRequest` requires `message`, not `text` (`enterprise_ops/schemas.py:7`).
- `IntelligenceHubPage.jsx:153` POSTs `{ text, language }` to `/document-intelligence/run`. Backend `DocumentIntelligenceInput` requires `content`, not `text` (`document_intelligence/schemas.py:5`).
- `IntelligenceHubPage.jsx:242` POSTs JSON `{ text, language }` to `/analyze/text`. Backend route requires Form fields `content` + `language` (`analyze.py:370-374`).

The older `AnalyzePage.jsx:102` uses correct `FormData` for the same `/analyze/text` route — drift is localized to Intelligence Hub.

**Impact**: High — 3 of the Hub's 3 tabs cannot submit at all.
**Effort**: S — one-line fixes per tab + a contract test per route.
**Source**: codex Gaps 6, 7, 8 only — verified.

### T3.4 — Chat-first preview opens a WebSocket path that doesn't exist

**Verified**:
- `usePreviewEvents.jsx:27` builds `${apiUrl}/ws/${runId}`. With `apiUrl = .../api`, this resolves to `/api/ws/{runId}`.
- Backend mounts the WS handler at `/api/executions/ws/{run_id}` (`executions.py:340` + `main.py:250` mounts router under `/api/executions`).
- The reference impl `useExecutionWS.js:32` does `.replace(/\/api$/, '/api/executions')` correctly. Drift is in `usePreviewEvents` only.

**Impact**: Med — chat-first preview never receives step status updates. Silent failure (no exception on WS connect-fail, just no events).
**Effort**: XS — copy the URL builder from `useExecutionWS`.
**Source**: codex Gap 9 only — verified.

### T3.5 — Frontend "API docs" page links to disabled docs + lists wrong API-key endpoint

**Verified**:
- `ApiDocsPage.jsx:8` derives `docsUrl = apiUrl.replace('/api', '/docs')`. `main.py:154-158` disables `/docs`, `/redoc`, and `/openapi.json` when `settings.debug` is false → 404 in production.
- `ApiDocsPage.jsx:51` documents `POST /api/api-keys`, but `auth/api_keys.py:123` exposes `POST /api/api-keys/generate`. The bare root POST does not exist.

**Impact**: Med — in-app docs lead production users to 404 + a non-existent route.
**Effort**: S — replace the Swagger link with a static endpoint reference + fix the API-key row.
**Source**: codex Gap 11 only — verified.

## Tier 4 — Single-source, not yet inspected — review before acting

The third Claude session reported these as headlines without me having access to its full evidence (file is missing from disk). **Verify each by direct grep before acting.**

| Claim | Source | Status |
|---|---|---|
| Operational scripts `seed_tenant_alpha.py` + `persist_showcase.py` need admin endpoints | 3rd Claude | not verified |
| Dead duplicate auth router | 3rd Claude | not verified |
| Generated scaffolds raising NotImplementedError | 3rd Claude | not verified |
| Double zombie-cleaner | 3rd Claude | not verified |
| Inflated `apps_generated` counts | 3rd Claude | not verified |
| Healing-strategy promise without list endpoint | 3rd Claude | not verified |
| `DEPLOYMENT.md:459` references nonexistent `GET /api/health/ready` | codex Gap 12 | not verified |
| C# test generator emits `Assert.True(true); // TODO` placeholders | codex Gap 14 | not verified |

## Tier 5 — Discarded

- My Gap 8 ("refresh-tokens frontend interceptor work has no visible tracking") — not a code gap; just an issue-tracker complaint. Acknowledged as informational.
- Codex's confession about possibly auditing the wrong repo: codex was at commit `ec79bd2` (~28 commits behind master), but inspection confirms its findings target the same files that exist in current master. No findings invalidated by the staleness.
- The missing third-Claude audit file: I asked Christian to confirm where it landed. Triangulation is robust without the full file because the headlines were specific enough to verify.

## Recommended triage order

| Phase | Items | Effort | Why this order |
|---|---|---|---|
| **1. Wire** (today, ≤1h) | T1.1 + T3.4 (WS path) | 30-45 min | Loudest user-facing breakage. T1.1 unblocks 3 documented features (Portfolio Copilot, Evaluation, etc.). |
| **2. Contract fixes** (today, ≤1h) | T3.3 (Intelligence Hub × 3) + T3.5 (API docs page) | 30 min | All five 422/404 bugs are 1-line fixes against verified evidence. |
| **3. Audit + cron** (this week) | T3.1 + T3.2 | 2-3h each | Real correctness bugs but nuanced — pick one canonical audit table, swap cron parser for `croniter`, add tests. |
| **4. Doc cleanup** (after 1+2) | T2.1 + T2.2 | 1h | Wait until wiring is final so the docs reflect reality. |
| **5. Review tier 4** | each line above | varies | Spend 5 min per item to grep-verify. Promote to a real gap or close. |
| **6. Test debt** | T1.2 | 5-10h | Last; do once the surface is stable. |

## What I'd actually ship next

If we resume tomorrow with one focused session: **Phase 1 + Phase 2 together** is one PR (~10 file edits, ~80 LOC, plus 3-5 contract tests). Closes 8 verified bugs in one bounded change. Effort: ≤2h.

Phase 3 (audit shadow + cron) is its own PR — both touch persistence/scheduling correctness and need careful test coverage; rushing them with the wiring fixes risks landing two regressions in one commit.
