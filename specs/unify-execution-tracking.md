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

## Acceptance Criteria

- [ ] All 6 use-case routes write to workflow_runs (not pipeline_runs)
- [ ] Dashboard KPIs read from workflow_runs ONLY (no UNION needed)
- [ ] Ejecuciones page shows ALL runs (automations + use-cases)
- [ ] Dashboard Recientes shows ALL runs (from workflow_runs)
- [ ] pipeline_runs receives NO new writes
- [ ] 260/260 tests pass
- [ ] Existing historical data in pipeline_runs is not deleted

## Files to Modify

- `backend/app/utils/run_tracker.py` — extend with new params
- `backend/app/routes/swarms.py` — replace save_pipeline_run
- `backend/app/routes/enterprise_ops.py` — same
- `backend/app/routes/document_intelligence.py` — same
- `backend/app/routes/analyze.py` — same
- `backend/app/routes/drive_pipeline.py` — same
- `backend/app/routes/portfolio_copilot.py` — same
- `backend/app/routes/workflow_runs.py` — simplify queries
- `backend/app/db/migrations/028_workflow_runs_agents_used.sql` — new migration
