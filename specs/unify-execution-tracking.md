# Spec: Unify Execution Tracking — Migrate to Single Source of Truth

## Context

NexusForge currently has TWO execution tracking tables that cause data inconsistency:

1. **`workflow_runs`** — written by the DAG executor (automations, direct workflow executions)
2. **`pipeline_runs`** — written by use-case routes (enterprise_ops, swarms, analyze, drive_pipeline, document_intelligence, portfolio_copilot)

The Dashboard reads `pipeline_runs` for "Ejecuciones Recientes" but `workflow_runs` for KPIs, causing users to see 50 executions in the table but 0 in the counters.

## Goal

Migrate ALL execution tracking to use ONLY `workflow_runs` + `step_executions`. Make `pipeline_runs` a readonly legacy table that is no longer written to. Every execution from every source must flow through the same tracking pipeline so Dashboard KPIs, Ejecuciones page, and Automation stats all show consistent numbers.

## Current Architecture (BROKEN)

```
Automations → POST /automations/{id}/run → executor.py → workflow_runs ✅
Workflows  → POST /executions/          → executor.py → workflow_runs ✅
Swarms     → POST /swarms/execute       → save_pipeline_run() → pipeline_runs ❌
Enterprise → POST /enterprise-ops/process → save_pipeline_run() → pipeline_runs ❌
DocIntel   → POST /document-intelligence/run → save_pipeline_run() → pipeline_runs ❌
Analyze    → POST /analyze               → save_pipeline_run() → pipeline_runs ❌
Drive      → POST /drive-to-intelligence  → save_pipeline_run() → pipeline_runs ❌
Portfolio  → POST /portfolio-copilot/run  → save_pipeline_run() → pipeline_runs ❌
```

## Target Architecture (UNIFIED)

```
ALL SOURCES → run_tracker.start_run() → workflow_runs
           → run_tracker.record_step() → step_executions
           → run_tracker.complete_run() → workflow_runs (status, tokens, cost)
           → Dashboard reads workflow_runs ONLY
```

## Tasks

### Task 1: Audit all writers to pipeline_runs

Read these files and find every `save_pipeline_run()` or `INSERT INTO pipeline_runs` call:

- `backend/app/routes/swarms.py` — find where `save_pipeline_run` is called
- `backend/app/routes/enterprise_ops.py` — find where pipeline_runs is written
- `backend/app/routes/document_intelligence.py` — same
- `backend/app/routes/analyze.py` — same
- `backend/app/routes/drive_pipeline.py` — same
- `backend/app/routes/portfolio_copilot.py` — same
- `backend/app/utils/run_tracker.py` — the existing run_tracker that writes to workflow_runs

For each file, document:
- What data it currently saves to pipeline_runs (columns: pipeline_name, status, agents_used, total_tokens, cost_usd, processing_time_ms, notion_url, file_name, etc.)
- What data it ALSO saves to workflow_runs via run_tracker (if any)
- What the function signature looks like

### Task 2: Extend run_tracker to capture all pipeline_runs data

The existing `run_tracker.py` has `start_run()`, `record_step()`, `complete_run()`. It writes to `workflow_runs` but does NOT capture fields that only exist in `pipeline_runs`:

- `pipeline_name` → map to workflow_runs.metadata or a new column
- `agents_used` → workflow_runs already has this column (may need populating)
- `file_name`, `document_type`, `trigger_source` → put in workflow_runs.metadata JSONB
- `notion_url`, `webhook_sent` → put in workflow_runs.metadata JSONB
- `processing_time_ms` → compute from completed_at - started_at

Create a migration `028_workflow_runs_agents_used.sql`:
```sql
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS agents_used JSONB DEFAULT '[]';
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS pipeline_name VARCHAR(100) DEFAULT NULL;
```

Update `run_tracker.py`:
- `start_run()` should accept `pipeline_name` and `agents_used` parameters
- `complete_run()` should accept `agents_used`, `notion_url`, and `extra_metadata`
- All data that was going to pipeline_runs now goes to workflow_runs

### Task 3: Migrate each route file

For each use-case route, replace `save_pipeline_run()` with `run_tracker`:

**Pattern for each file:**

```python
# BEFORE (writes to pipeline_runs):
from app.db.client import get_db_pool
run_id = await save_pipeline_run(
    pipeline_name="enterprise_operations",
    agents_used=["intake", "classifier", ...],
    total_tokens=total_tokens,
    cost_usd=total_cost,
    ...
)

# AFTER (writes to workflow_runs via run_tracker):
from app.utils.run_tracker import start_run, record_step, complete_run
run_id = await start_run(
    workflow_id=None,  # use-case runs have no workflow
    pipeline_name="enterprise_operations",
    user_id=user_id,
    trigger_type="api",
    metadata={"trigger_source": "enterprise_ops", "file_name": file_name}
)
# ... execute agents ...
for step_result in results:
    await record_step(run_id, step_result["agent"], step_result)
await complete_run(
    run_id,
    status="completed",
    total_tokens=total_tokens,
    total_cost=total_cost,
    agents_used=agents_list,
    metadata={"notion_url": notion_url, "webhook_sent": True}
)
```

Files to migrate (in order):
1. `backend/app/routes/swarms.py`
2. `backend/app/routes/enterprise_ops.py`
3. `backend/app/routes/document_intelligence.py`
4. `backend/app/routes/analyze.py`
5. `backend/app/routes/drive_pipeline.py`
6. `backend/app/routes/portfolio_copilot.py`

### Task 4: Update Dashboard queries

After migration, all data is in `workflow_runs`. Simplify:

**`backend/app/routes/workflow_runs.py`:**
- `_get_db_runs()` — change `FROM pipeline_runs` to `FROM workflow_runs` with same column mapping
- `_get_db_health()` — remove the UNION query, just read `FROM workflow_runs`
- Agent activity — read `agents_used` from `workflow_runs` only

**`backend/app/routes/executions.py`:**
- `list_executions` already reads `workflow_runs` — now it shows ALL runs (automations + use-cases)

### Task 5: Verify the full flow

After migration, test each path:

1. **POST /swarms/execute** → verify run appears in:
   - GET /runs/ (Dashboard Recientes) ✅
   - GET /runs/reliability/health (KPIs) ✅
   - GET /executions/ (Ejecuciones page) ✅

2. **POST /enterprise-ops/process** → same verification

3. **POST /automations/{id}/run** → same verification (should still work)

4. **Dashboard KPIs** should now show combined totals from a SINGLE table

5. **pipeline_runs table** should have NO new inserts after migration

### Task 6: Mark pipeline_runs as legacy

Add a comment to the table migration and any remaining references:
```sql
-- LEGACY: pipeline_runs is no longer written to.
-- All new executions go to workflow_runs.
-- This table is kept for historical data only.
```

### Task 7: Ejecuciones desde Flujos de Trabajo

When a user clicks "Run" from WorkflowDetailPage or WorkflowBuilderPage, it calls `POST /executions/` which goes through `trigger_execution` in `executions.py`. This ALREADY writes to `workflow_runs` via the executor — no migration needed. But verify:

- `POST /executions/` → `trigger_execution()` → creates `workflow_runs` row ✅
- The run MUST have `user_id` set (currently it does via `_get_user_id`)
- The run MUST appear in Dashboard KPIs after completion
- The run MUST appear in the Ejecuciones page
- Steps MUST appear in `step_executions` with tokens/cost per agent

**Key check:** When the executor calls `execute_workflow()`, it already does:
- INSERT workflow_runs (pending)
- For each step: INSERT step_executions (with tokens_used, cost_usd)
- UPDATE workflow_runs (completed, total_tokens, total_cost_usd)

This flow is already unified. No changes needed. But verify it works end-to-end.

### Task 8: Métricas de Costo page (/metrics)

The Cost/Token Dashboard (`CostTokenDashboard.jsx`) reads from:
- `GET /runs/reliability/health` → total_tokens, total_cost (same as Dashboard KPIs)
- `GET /runs/` → per-run breakdown with tokens and cost
- `GET /providers/status` → which LLM providers are active

After migration to single table, these all read from `workflow_runs`. Verify:

1. **Total tokens** = SUM of all workflow_runs.total_tokens (should be > 0 after real LLM calls)
2. **Total cost** = SUM of all workflow_runs.total_cost_usd
3. **Per-run breakdown** = each workflow_run row has its own tokens/cost
4. **Per-agent breakdown** = from agents_used JSONB column cross-referenced with step_executions

**Critical:** After the _extract_text() fix is deployed, agents should use real LLM calls (not fallback), so tokens and cost will be > 0. Before that fix, all executions show $0 / 0 tokens because agents fall back to demo mode.

**Métricas flow:**
```
Agent executes → LLMRouter.chat() → GroqProvider returns {tokens_input, tokens_output}
  → AgentResult.tokens_used = tokens_input + tokens_output
  → AgentResult.cost_usd = calculate_cost(provider, tokens_input, tokens_output)
  → step_runner saves to step_executions (tokens_used, cost_usd)
  → executor sums all steps → UPDATE workflow_runs (total_tokens, total_cost_usd)
  → GET /runs/reliability/health reads SUM from workflow_runs
  → Dashboard KPIs + Métricas page display correct totals
```

**What can cause tokens=0:**
- Agent enters demo mode (no text found in input) → FIX: _extract_text()
- LLM API key invalid → check Render env vars
- LLM call fails, agent uses fallback → fallback returns tokens_used=0
- Groq model deprecated → check model availability
- cost_usd not calculated → verify token_tracker.py has correct pricing

### Task 9: Verify cost tracking end-to-end

Read `backend/app/llm/token_tracker.py` and verify:
- Groq pricing is correct and up-to-date
- Claude pricing is correct
- `calculate_cost(provider, tokens_input, tokens_output)` returns > 0 for non-zero tokens
- The cost is attached to `LLMResponse.cost_usd` in the router

Then verify the chain:
1. `LLMRouter.chat()` → `response.cost_usd = calculate_cost(...)` 
2. `agent.execute()` → `AgentResult(cost_usd=resp.cost_usd)`
3. `step_runner.run_step()` → saves to `step_executions.cost_usd`
4. `executor.execute_workflow()` → `total_cost += result.get("cost_usd", 0)`
5. `executor` → `UPDATE workflow_runs SET total_cost_usd = $N`
6. `_get_db_health()` → `SUM(total_cost_usd)` from workflow_runs
7. Frontend KPI → displays `$X.XXXX`

### Task 10: Connectors page (/connectors)

Connectors are user-scoped CRUD (Gmail, Slack, Notion, Drive, REST, Postgres). They do NOT create executions — they are used BY executions as output destinations. But verify:

- When a connector `test_connection` is called, it should NOT create a workflow_run
- When a connector `fetch` or `push` is called during a pipeline, the parent run tracks it
- The ConnectorHubPage shows test status per connector — this is independent of execution tracking

No changes needed for connectors in this spec. They are consumers, not producers.

### Task 11: Audit Log page (/audit)

The audit log reads from `audit_logs` table — completely separate from execution tracking. Verify:

- Audit entries are written when: automations CRUD, workflows CRUD, agent config changes, variable changes
- Audit does NOT track individual execution runs (that's workflow_runs)
- No changes needed

### Task 12: Intelligence Hub page (/intelligence)

This page has 3 tabs that each trigger use-case routes:
- Enterprise Ops tab → POST /enterprise-ops/process → currently writes pipeline_runs → MIGRATE
- Doc Intelligence tab → POST /document-intelligence/run → currently writes pipeline_runs → MIGRATE
- Analyze tab → POST /analyze/text → currently writes pipeline_runs → MIGRATE

All 3 are covered in Tasks 3. After migration, runs from Intelligence Hub appear in:
- Dashboard KPIs ✅
- Dashboard Recientes ✅
- Ejecuciones page ✅
- Métricas de Costo ✅

### Task 13: Status page (/status)

Reads from GET /health (DB + Redis check) and GET /providers/status. Does NOT read execution data. No changes needed.

### Task 14: API Docs page (/docs)

Static page with health check. No execution data. No changes needed.

### Task 15: Agents page (/agents)

Shows 24 registered agents with config. The "Actividad de Agentes" panel and memory stats should reflect actual agent usage from executions.

After migration, agent activity should be computed from:
```sql
SELECT agent_type, COUNT(*) as executions, 
       AVG(duration_ms) as avg_latency, SUM(tokens_used) as total_tokens
FROM step_executions 
GROUP BY agent_type
```
This is already the correct source — step_executions is written by ALL execution paths (executor + step_runner). No migration needed here.

### Task 16: Swarms page (/swarms)

POST /swarms/execute triggers a swarm that currently writes to BOTH tables. After migration (Task 3), it only writes to workflow_runs. The swarm result should appear in all dashboards.

## Complete Page → Data Source Map (After Migration)

| Page | API | Source Table | Writes? |
|------|-----|-------------|---------|
| Dashboard KPIs | GET /runs/reliability/health | workflow_runs | Read |
| Dashboard Recientes | GET /runs/ | workflow_runs | Read |
| Dashboard Agentes | GET /runs/reliability/health | workflow_runs.agents_used + step_executions | Read |
| Automatizaciones stats | GET /automations/{id}/stats | workflow_runs | Read |
| Automatizaciones dashboard | GET /automations/{id}/dashboard | workflow_runs | Read |
| Automatizaciones run | POST /automations/{id}/run | workflow_runs | Write |
| Wizard publish | POST /workflows/ + POST /automations/ | workflows + automations | Write |
| Ejecuciones lista | GET /executions/ | workflow_runs | Read |
| Ejecuciones detalle | GET /executions/{id} | workflow_runs + step_executions | Read |
| Ejecuciones run | POST /executions/ | workflow_runs | Write |
| Métricas costo | GET /runs/reliability/health | workflow_runs | Read |
| Métricas per-run | GET /runs/ | workflow_runs | Read |
| Intelligence Enterprise | POST /enterprise-ops/process | workflow_runs (MIGRATED) | Write |
| Intelligence DocIntel | POST /document-intelligence/run | workflow_runs (MIGRATED) | Write |
| Intelligence Analyze | POST /analyze/text | workflow_runs (MIGRATED) | Write |
| Swarms execute | POST /swarms/execute | workflow_runs (MIGRATED) | Write |
| Drive Pipeline | POST /drive-to-intelligence | workflow_runs (MIGRATED) | Write |
| Portfolio Copilot | POST /portfolio-copilot/run | workflow_runs (MIGRATED) | Write |
| Agentes activity | computed from step_executions | step_executions | Read |
| Status | GET /health | N/A | Read |
| Connectors | CRUD /connectors/ | connectors table | Write |
| Audit | GET /audit/ | audit_logs table | Read |
| Settings | localStorage + /auth/* | nf_users | Read/Write |

## Acceptance Criteria

- [ ] All 6 use-case routes write to workflow_runs (not pipeline_runs)
- [ ] Dashboard KPIs read from workflow_runs ONLY (no UNION needed)
- [ ] Ejecuciones page shows ALL runs (automations + use-cases)
- [ ] Dashboard Recientes shows ALL runs (from workflow_runs)
- [ ] Métricas de Costo shows correct tokens and cost from workflow_runs
- [ ] Actividad de Agentes shows agent usage from step_executions
- [ ] Intelligence Hub runs appear in Dashboard + Ejecuciones
- [ ] Swarm runs appear in Dashboard + Ejecuciones
- [ ] Workflow direct runs appear in Dashboard + Ejecuciones
- [ ] pipeline_runs receives NO new writes
- [ ] 260/260 tests pass
- [ ] Existing historical data in pipeline_runs is not deleted
- [ ] Cost tracking chain verified end-to-end (LLM → AgentResult → step_executions → workflow_runs → KPI)

## Files to Modify

- `backend/app/utils/run_tracker.py` — extend with pipeline_name, agents_used params
- `backend/app/routes/swarms.py` — replace save_pipeline_run with run_tracker
- `backend/app/routes/enterprise_ops.py` — same
- `backend/app/routes/document_intelligence.py` — same
- `backend/app/routes/analyze.py` — same
- `backend/app/routes/drive_pipeline.py` — same
- `backend/app/routes/portfolio_copilot.py` — same
- `backend/app/routes/workflow_runs.py` — simplify to read workflow_runs only
- `backend/app/llm/token_tracker.py` — verify pricing is correct
- `backend/app/db/migrations/028_workflow_runs_agents_used.sql` — new migration
