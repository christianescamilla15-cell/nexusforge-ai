# Design: Unify Execution Tracking

## Technical Design

> Architecture: Unified Polymorphic Table (n8n pattern) + Counter Projections (ClickHouse pattern)
> Sources: Temporal.io, n8n, Inngest, Databricks Lakeflow, PostgreSQL pg_ivm

### Database Migration 028 — Unified Polymorphic Execution Table

```sql
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS execution_type VARCHAR(30) DEFAULT 'dag_workflow';
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS automation_id UUID;
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS pipeline_name VARCHAR(100);
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS agents_used JSONB DEFAULT '[]';
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS trigger_source VARCHAR(50);
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS input_data JSONB;
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS output_data JSONB;

CREATE INDEX IF NOT EXISTS idx_runs_execution_type ON workflow_runs(execution_type);
CREATE INDEX IF NOT EXISTS idx_runs_automation ON workflow_runs(automation_id);
```

### Database Migration 029 — Counter Projections (instant KPIs)

```sql
CREATE TABLE IF NOT EXISTS user_execution_stats (
    user_id UUID PRIMARY KEY,
    total_runs INTEGER DEFAULT 0,
    runs_completed INTEGER DEFAULT 0,
    runs_failed INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd NUMERIC(12,6) DEFAULT 0,
    last_run_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE OR REPLACE FUNCTION update_execution_stats() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_execution_stats (user_id, total_runs, runs_completed, runs_failed, total_tokens, total_cost_usd, last_run_at)
    VALUES (NEW.user_id, 1,
        CASE WHEN NEW.status='completed' THEN 1 ELSE 0 END,
        CASE WHEN NEW.status='failed' THEN 1 ELSE 0 END,
        COALESCE(NEW.total_tokens,0), COALESCE(NEW.total_cost_usd,0), NEW.started_at)
    ON CONFLICT (user_id) DO UPDATE SET
        total_runs=user_execution_stats.total_runs+1,
        runs_completed=user_execution_stats.runs_completed+EXCLUDED.runs_completed,
        runs_failed=user_execution_stats.runs_failed+EXCLUDED.runs_failed,
        total_tokens=user_execution_stats.total_tokens+EXCLUDED.total_tokens,
        total_cost_usd=user_execution_stats.total_cost_usd+EXCLUDED.total_cost_usd,
        last_run_at=GREATEST(user_execution_stats.last_run_at,EXCLUDED.last_run_at),
        updated_at=now();
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_execution_stats AFTER INSERT ON workflow_runs
FOR EACH ROW EXECUTE FUNCTION update_execution_stats();
```

### Extend run_tracker.py

Current `start_run()`, `record_step()`, `complete_run()` write to workflow_runs + step_executions. Extend to accept:
- `pipeline_name` parameter (maps legacy pipeline_runs.pipeline_name)
- `agents_used` parameter (JSONB list of agent names)
- `extra_metadata` parameter (notion_url, webhook_sent, file_name, etc.)

### Migrate 6 Route Files

Replace every `save_pipeline_run()` call with `run_tracker` calls:

Pattern:
```python
# BEFORE:
run_id = await save_pipeline_run(pipeline_name="enterprise_operations", agents_used=[...], ...)

# AFTER:
from app.utils.run_tracker import start_run, record_step, complete_run
run_id = await start_run(workflow_id=None, pipeline_name="enterprise_operations", user_id=user_id)
for step in results:
    await record_step(run_id, step["agent"], step)
await complete_run(run_id, status="completed", total_tokens=total, agents_used=[...])
```

Files: swarms.py, enterprise_ops.py, document_intelligence.py, analyze.py, drive_pipeline.py, portfolio_copilot.py

### Simplify Dashboard Queries

After migration, `workflow_runs.py`:
- `_get_db_runs()` reads FROM workflow_runs (not pipeline_runs)
- `_get_db_health()` reads FROM workflow_runs only (no UNION)
- Agent activity reads agents_used FROM workflow_runs + step_executions

### Automation "Ejecutar" Stays on Page

In 5 typed dashboards (TicketDashboard, DocumentDashboard, EmailDashboard, ReportDashboard, GenericDashboard):
- After POST /automations/{id}/run, do NOT navigate to /executions/{runId}
- Instead: poll /executions/{runId} every 1.5s, update stats inline
- Show result in the dashboard when complete
- Add "Ver detalle" link in results table for optional navigation

### Frontend Sync Architecture (from TanStack Query + Zustand research)

**Query Key Factory** (`frontend/src/shared/queryKeys.js`):
```javascript
export const keys = {
  dashboardKpis: () => ['dashboard', 'kpis'],
  automations: () => ['automations'],
  automation: (id) => ['automations', id],
  executions: () => ['executions'],
  analytics: () => ['analytics'],
}
```

**After any execution completes, invalidate all related caches:**
```javascript
// In every component that triggers a run:
onSettled: async () => {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: keys.automations() }),
    queryClient.invalidateQueries({ queryKey: keys.dashboardKpis() }),
    queryClient.invalidateQueries({ queryKey: keys.executions() }),
    queryClient.invalidateQueries({ queryKey: keys.analytics() }),
  ])
}
```

**Counter Cache Trigger** (Migration 029 already includes this):
- PostgreSQL trigger auto-updates user_execution_stats on every INSERT
- Dashboard KPIs read from user_execution_stats (1 row, <1ms)
- No need for COUNT(*) full table scan

### Demo → Wizard Prefill

In DashboardPage.jsx "Crear automatización con esto" button:
- Save demo result to localStorage key `nxf_wizard_prefill`
- In WizardPage.jsx on mount: read prefill, set automationType, customName, description, inputType, outputTypes
- Clear prefill from localStorage after reading

### Wizard Smart Defaults

When user selects a type, also pre-fill:
- customName (e.g., "Triage de Tickets de Soporte")
- description (e.g., "Clasificar tickets por urgencia y generar respuestas automáticas")
- Currently only input/output are pre-filled via QUICK_TYPE_DEFAULTS

## Sync Map: Each Execution Origin → Where It Reflects

| Origin | Reflects In |
|--------|------------|
| Enjambre | Dashboard KPIs + Recientes + Agentes, Ejecuciones, Métricas, Status |
| Automation | Automation dashboard + card, Dashboard KPIs + Recientes + Agentes + Runs/Day + Plan Usage, Ejecuciones, Métricas, Workflows history, Notifications |
| Workflow directo | Dashboard KPIs + Recientes + Agentes, Ejecuciones, Métricas, Workflows history |
| Enterprise/DocIntel/Analyze | Intelligence Hub inline, Dashboard KPIs + Recientes + Agentes, Ejecuciones, Métricas, Email, Notion |
| Drive Pipeline | Dashboard KPIs + Recientes, Ejecuciones, Métricas, Notion, Email, WhatsApp, Webhook |
| Demo (Try AI Now) | NOTHING (not tracked) |
