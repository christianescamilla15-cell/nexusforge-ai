# Design: Unify Execution Tracking

## Technical Design

### Database Migration

Create migration `028_workflow_runs_agents_used.sql`:
```sql
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS agents_used JSONB DEFAULT '[]';
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS pipeline_name VARCHAR(100) DEFAULT NULL;
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
- Instead: poll in background, update stats inline, show result in the dashboard
- Add "Ver detalle" link in results table for optional navigation

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
