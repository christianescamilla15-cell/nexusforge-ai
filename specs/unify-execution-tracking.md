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

### Task 16: Swarms page (/swarms) — FULL SYNC REQUIREMENTS

POST /swarms/execute triggers a swarm (sequential, parallel, hierarchical, debate, consensus, adaptive). Each swarm calls real agents. After migration, a swarm execution MUST appear in ALL of these:

**Where a swarm run MUST be visible after execution:**

1. **Dashboard → KPIs** — "Ejecuciones Totales" must increment by 1, "Tasa de Exito" must update, tokens and cost must sum
2. **Dashboard → Ejecuciones Recientes** — new row with status=Completado, topology name, latency
3. **Dashboard → Actividad de Agentes** — each agent used in the swarm must increment its count
4. **Ejecuciones page (sidebar)** — the run must appear in the executions list with all steps
5. **Ejecuciones → Detalle** — clicking the run must show each agent step with input/output/tokens/cost
6. **Métricas de Costo** — total_tokens and total_cost from the swarm must be included in the aggregates
7. **Flujos de Trabajo** — if the swarm used a workflow_id, it appears in that workflow's run history

**Data that must be tracked per swarm execution:**

```
workflow_runs row:
  - id: UUID
  - workflow_id: NULL (swarms don't use a workflow)
  - pipeline_name: "swarm_{topology}" (e.g., "swarm_consensus")
  - status: "completed" | "failed"
  - trigger_type: "api"
  - user_id: from JWT
  - agents_used: ["classifier", "extractor", "summarizer"] (JSONB)
  - total_tokens: SUM of all agent tokens
  - total_cost_usd: SUM of all agent costs
  - started_at, completed_at: timestamps
  - metadata: {"topology": "consensus", "task": "...", "agents_count": 3}

step_executions rows (one per agent called):
  - run_id: linked to workflow_runs.id
  - step_name: agent_type (e.g., "classifier")
  - agent_type: same
  - status: "completed" | "failed"
  - tokens_used: from AgentResult
  - cost_usd: from AgentResult
  - duration_ms: measured
  - input_data: what the agent received
  - output_data: what the agent returned
```

**Current problem:** swarms.py writes to pipeline_runs (which Dashboard Recientes reads) but NOT to step_executions (so no per-agent breakdown). The swarm also calls `agent.execute()` directly instead of `agent.run()`, which means:
- No circuit breaker check per agent
- No memory recall/remember per agent
- No per-step DB tracking in step_executions

**Fix:** After the run_tracker migration, swarms should:
1. Call `start_run()` → creates workflow_runs row
2. For each agent result, call `record_step()` → creates step_executions row
3. Call `complete_run()` → updates workflow_runs with totals
4. Optionally: consider calling `agent.run()` instead of `agent.execute()` to get full lifecycle (circuit breaker + memory). This is a bigger change and can be done separately.

### Task 17: Tab Métricas dentro de Ejecuciones

The "Métricas" tab inside the Ejecuciones page (ExecutionListPage.jsx) embeds `CostTokenDashboard` component. This shows:

- **Tokens Totales** (e.g., 28,000) — from GET /runs/reliability/health → total_tokens
- **Costo Total USD** (e.g., $0.1047) — from same endpoint → total_cost
- **Latencia Prom.** (e.g., 542ms) — from same endpoint → avg_latency_ms
- **Total Reintentos** — from per-agent data → sum of retries
- **Total Fallbacks** — from per-agent data → sum of fallbacks
- **Tasa de Exito** (e.g., 100%) — from same endpoint → system_success_rate
- **Per-Run Breakdown table** — from GET /runs/ → each run with tokens/cost
- **Per-Agent Breakdown table** — from GET /runs/reliability/health → agents array

**CRITICAL:** This tab currently shows REAL data (28,000 tokens) because `_get_db_health()` currently reads from `pipeline_runs` which has actual swarm/enterprise_ops data. The Dashboard KPIs show 0 because they read from a different source.

After the UNION fix (commit 4970b91 pending deploy) or full migration to workflow_runs, ALL of these must show consistent data:
- Dashboard KPIs = Tab Métricas KPIs = same numbers
- Dashboard Recientes = Tab Ejecuciones list = same runs
- Both read from the SAME unified source

**The "Reintentos" and "Fallbacks" counters** come from per-agent data in the health endpoint. Currently these are always 0 because:
- `pipeline_runs` stores `agents_used` as a list of names but no retry/fallback counts
- `step_executions` has `retry_count` but is not aggregated in the health query

After migration, the health query should also compute:
```sql
SELECT agent_type, 
       SUM(retry_count) as total_retries,
       COUNT(*) FILTER (WHERE provider = 'local' AND model = 'fallback') as total_fallbacks
FROM step_executions 
GROUP BY agent_type
```

This gives real retry and fallback counts per agent.

### Task 18: Automation "Ejecutar" debe quedarse en la página

**BUG ACTUAL:** Cuando el usuario hace click en "Ejecutar" desde el dashboard de una automatización (ej: Invoice Data Extraction), el frontend navega a la página de Ejecuciones (`/executions/{runId}`), sacando al usuario de su contexto. El usuario pierde de vista su automation dashboard.

**Comportamiento esperado:** Al dar click en "Ejecutar":
1. El botón cambia a "Ejecutando..." con spinner
2. La ejecución corre en background
3. El usuario se QUEDA en el dashboard de la automatización
4. Los stats se actualizan en tiempo real (total_ejecuciones++, tasa de éxito recalcula)
5. Una nueva fila aparece en "Ejecuciones recientes" de ESA automatización
6. Notification bell muestra "Completado" cuando termina
7. El usuario puede OPCIONALMENTE navegar al detalle de la ejecución desde la tabla

**Fix en frontend:** En los 5 typed dashboards (TicketDashboard, DocumentDashboard, EmailDashboard, ReportDashboard, GenericDashboard), después de POST /automations/{id}/run:
- NO navegar a /executions/{runId}
- En su lugar: poll en background + actualizar stats + mostrar resultado inline
- Agregar link "Ver detalle" en la tabla de resultados que lleva a /executions/{runId}

### Task 19: Mapa completo de sincronizaciones por origen de ejecución

Cada ejecución desde CUALQUIER origen debe reflejarse en múltiples páginas:

**ENJAMBRE (POST /swarms/execute):**
```
Se refleja en:
├── Enjambres → modal de resultado
├── Ejecuciones (sidebar) → nueva fila con steps de cada agente
├── Tab Métricas → tokens + cost + per-agent
├── Dashboard KPIs → +1 ejecución, tokens, cost, tasa éxito
├── Dashboard Recientes → nueva fila "swarm_{topology}"
├── Dashboard Actividad Agentes → +1 por agente usado
├── Agentes → contador de ejecuciones por agente
└── Status → health scores actualizados
```

**AUTOMATIZACIÓN (POST /automations/{id}/run):**
```
Se refleja en:
├── Dashboard Automatización → total+1, tasa éxito, duración, costo, gráfica, tabla recientes
├── Card en Automatizaciones lista → "🔄 N ejecuciones", fecha última
├── Ejecuciones (sidebar) → nueva fila con todos los steps del DAG
├── Tab Métricas → tokens + cost + per-agent
├── Dashboard KPIs → +1 ejecución, tokens, cost, tasa éxito
├── Dashboard Recientes → nueva fila con nombre de automation
├── Dashboard Actividad Agentes → +1 por agente del pipeline
├── Dashboard Runs por Día → +1 en gráfica del día
├── Dashboard Plan Usage Bar → runs_today +1
├── Flujos de Trabajo → historial del workflow asociado
├── Agentes → contador por agente
├── NotificationBell → "Completado" o "Fallido"
├── Tab title → "(1) NexusForge AI"
├── Email → reporte HTML (si Resend configurado)
├── Slack → Block Kit message (si webhook configurado)
├── Pending Approvals → si requires_approval=true
└── Status → health scores
```

**WORKFLOW DIRECTO (POST /executions/):**
```
Se refleja en:
├── Ejecuciones (sidebar) → nueva fila
├── Ejecución Detalle → steps con input/output/tokens/cost
├── Tab Métricas → tokens + cost
├── Dashboard KPIs → +1
├── Dashboard Recientes → nueva fila
├── Dashboard Actividad Agentes → +1 por agente
├── Flujos de Trabajo → historial del workflow
└── Status → health scores
```

**ENTERPRISE OPS / DOC INTEL / ANALYZE (Intelligence Hub):**
```
Se refleja en:
├── Intelligence Hub → resultado inline en el tab
├── Ejecuciones (sidebar) → nueva fila
├── Tab Métricas → tokens + cost
├── Dashboard KPIs → +1
├── Dashboard Recientes → nueva fila
├── Dashboard Actividad Agentes → +1 por agente
├── Email → reporte HTML
└── Notion → página creada (si configurado)
```

**DRIVE PIPELINE:**
```
Se refleja en:
├── Ejecuciones → nueva fila
├── Tab Métricas → tokens + cost
├── Dashboard KPIs → +1
├── Notion → página con resultados
├── Email → reporte
├── WhatsApp → mensaje (si Twilio configurado)
└── Webhook → POST al URL configurado
```

**DEMO (Try AI Now):**
```
Se refleja en:
└── NADA (no se trackea, rate-limited 5/hr/IP)
```

### Task 20: Reintentos y Fallbacks en Métricas

Los contadores "Total Reintentos" y "Total Fallbacks" en la tab Métricas están siempre en 0.

Después de la migración, estos deben calcularse desde step_executions:
```sql
-- Reintentos: steps que tuvieron retry_count > 0
SELECT SUM(retry_count) as total_retries FROM step_executions

-- Fallbacks: steps donde el agente usó fallback (provider='local', model='fallback')
SELECT COUNT(*) as total_fallbacks FROM step_executions
WHERE output_data::text LIKE '%"_parse_failed": true%'
   OR output_data::text LIKE '%"provider": "local"%'
```

Estos números deben actualizarse con cada nueva ejecución.

### Task 21: Dashboard Ejecuciones Recientes — límite visual + limpiar

**Problema actual:** La tabla de "Ejecuciones Recientes" en el Dashboard muestra 51 resultados sin límite, haciendo la página muy larga.

**Requerimientos:**

1. **Máximo 25 filas visibles** — si hay más de 25, la tabla se contrae con scroll interno (max-height) y paginación de 10 en 10
2. **Botón "Limpiar"** — permite borrar todas las ejecuciones recientes de un click (con ConfirmModal)
3. **Header sticky** — al scrollear dentro de la tabla, el header (Estado, Flujo, ID, Latencia) se mantiene fijo
4. **Contador** — "51 resultados" visible en el header
5. **No ocupar más de ~400px de alto** — si hay 51 resultados, se paginan y scrollean, no estiran la página

**Nota:** Este fix ya fue implementado parcialmente (commit d77f6a5 pendiente deploy) con:
- Paginación 10/page
- Max-height 400px con scroll
- Sticky header
- Botón "Limpiar" con ConfirmModal

Verificar que funciona correctamente después del deploy.

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
