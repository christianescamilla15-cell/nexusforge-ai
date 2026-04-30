# Tier 4 verification — 2026-04-30

> Closes the "needs review" tier of the gap-audit triangulation.
> Each claim was a single-source finding (mostly third-Claude
> session, two from codex) without me having access to the full
> evidence text. Each was verified by direct grep against current
> master. Result: 3 real gaps, 4 invalid (model artifact), 1
> judgment call.

## Real gaps (verified, fix or ship plan)

### #4 — Double zombie-cleaner ✅ verified
- **Source**: 3rd Claude session
- **Evidence**:
  - `backend/app/main.py:99-118` — `_zombie_cleanup_loop()` background task fires every 5 minutes during the lifespan.
  - `backend/app/routes/executions.py:119-137` — `POST /executions/cleanup-zombies` endpoint does the same SQL UPDATE manually.
- **Status**: real but non-blocking. The two implementations may serve different purposes (auto + admin manual trigger). Not a correctness bug, but the SQL string is duplicated and could drift. **Defer**: low impact, would benefit from refactoring into a shared `cleanup_zombies()` helper but not urgent.

### #7 — DEPLOYMENT.md references nonexistent `/api/health/ready` ✅ verified, fixed
- **Source**: codex Gap 12
- **Evidence**: `docs/DEPLOYMENT.md:459` documents `GET /api/health/ready` as the readiness probe. Pre-fix, `backend/app/routes/health.py` only exposed `/ping`, `/version`, `/health`. Any K8s/Render probe pointed at the documented path returned 404 → pod permanently `NotReady`.
- **Status**: **FIXED in this commit.** Added `GET /api/health/ready` that returns 200 only when DB + Redis both up; returns 503 otherwise (proper status-code probe, distinct from `/api/health` which always returns 200 with a degradation body, and `/api/ping` which doesn't touch deps). Smoke test in `tests/test_route_wiring.py::test_health_ready_route_exists`.

### #8 — C# test generator emits `Assert.True(true); // TODO` placeholders ✅ verified
- **Source**: codex Gap 14
- **Evidence**: `backend/app/refactor/cicd_generator.py:276` and `:290` emit `Assert.True(true); // TODO: implement real assertion` / `// TODO: implement` in generated xUnit test files.
- **Status**: real but low-impact. The platform claims to "generate xUnit/Jest/pytest tests" — these C# tests pass without exercising behavior, which is misleading. **Defer**: cleanest fix is to mark them `[Skipped("scaffold")]` or surface "scaffolding" in the test generator's response payload. Not blocking; left as a Tier 5 followup.

## Invalid (model artifact — discard)

### #2 — "Dead duplicate auth router" ❌ INVALID
- **Source**: 3rd Claude session
- **Evidence**: only ONE auth router exists (`backend/app/auth/routes.py:19` with `prefix="/auth"`). The "duplication" the third Claude saw was almost certainly the `auth/audit.py` shadowing of `routes/audit.py` — that was a different bug, real, and already closed in commit `1e03a9a` by moving `auth/audit.py` to `/activity`. There is no second auth router to delete.
- **Verdict**: Discard. False positive.

### #3 — "Generated scaffolds raising NotImplementedError" ❌ INVALID
- **Source**: 3rd Claude session
- **Evidence**: 3 hits for `NotImplementedError` in `backend/app/`:
  - `memory/anthropic_memory_tool.py:213` — `except (OSError, NotImplementedError)` (catching, not raising)
  - `memory/anthropic_memory_tool.py:341` — same pattern
  - `refactor/strangler_ui_generator.py:119` — emits `raise NotImplementedError("Wire to {legacy_stack} system")` INTO a generated scaffold file. That's intentional generated scaffolding — the strangler pattern expects the human to implement the wired adapter. Documented as such in the strangler module's docstring.
- **Verdict**: Discard. Each hit is either a defensive `except` clause or intentional template content for human completion.

### #5 — "Inflated `apps_generated` counts" ❌ INVALID (vague)
- **Source**: 3rd Claude session
- **Evidence**: `backend/app/synth/generator.py:45` defines `apps_generated: list[str]` and `:53` has a comment that explicitly distinguishes scope vs non-scope: "downstream tooling can distinguish [scope from non-scope stubs]". `:61` returns `len(apps_generated) + len(non_scope_stubs_generated)`. The naming is intentional: in-scope apps get into `apps_generated`, scaffolding stubs go to `non_scope_stubs_generated`. The "inflation" claim has no clear referent.
- **Verdict**: Discard absent more specific evidence. The current shape looks deliberate.

### #6 — "Healing-strategy promise without list endpoint" ❌ INVALID (judgment)
- **Source**: 3rd Claude session
- **Evidence**: CLAUDE.md says "Self-healing: 5 strategies". Backend exposes `/healing/stats` and `/healing/retry/{id}` (in `routes/memory.py`) but no `/healing/strategies` list endpoint. There is no caller demanding such an endpoint; the strategies are documented but not browsable.
- **Verdict**: Discard. Whether to add a list endpoint is a UX decision, not a correctness gap. Not a model artifact, but not an actionable gap either.

## Judgment call (kept open)

### #1 — Operational scripts (`seed_tenant_alpha.py`, `persist_showcase.py`) need admin endpoints
- **Source**: 3rd Claude session
- **Evidence**: Both files exist in `backend/scripts/`. They are operational tools (seed synthetic tenant data, persist showcase results) typically run via `render exec` or CLI, not user-facing.
- **Reasoning**: We did make `rotate_fernet_keys.py` admin-callable in commit `94eaf29` (T1 of triangulation triage). The same logic could apply here — but these are dev/showcase tools, not security-critical. The cost (an admin endpoint per script + auth + tests) probably exceeds the benefit (operators rarely need to trigger them, and `render exec` works fine).
- **Verdict**: Open as a low-priority enhancement, not shipped. Reconsider if a non-engineer ever needs to trigger these.

## Net result

| Status | Count | Items |
|---|---|---|
| Verified real, FIXED | 1 | #7 (added `/api/health/ready` route + smoke test) |
| Verified real, deferred | 2 | #4 (zombie cleaner dedup), #8 (C# test scaffolds) |
| Invalid (model artifact) | 4 | #2, #3, #5, #6 |
| Judgment call (open) | 1 | #1 (showcase script admin endpoints) |

**Triangulation lesson confirmed**: 1/3-evidence claims are NOT all signal. Without verification, half of the third-Claude headlines were false positives. The triangulation rule "verify by inspection, then fix if real" is the correct one — never trust a single-source finding without a grep check.
