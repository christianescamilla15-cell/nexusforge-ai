# Tasks: Unify Execution Tracking

## Phase 1: Database Migration (Tasks 1-6)

- [ ] 1. Audit all `save_pipeline_run()` calls in: swarms.py, enterprise_ops.py, document_intelligence.py, analyze.py, drive_pipeline.py, portfolio_copilot.py
- [ ] 2. Create migration `028_workflow_runs_agents_used.sql` — add `agents_used JSONB` and `pipeline_name VARCHAR` columns to workflow_runs
- [ ] 3. Extend `backend/app/utils/run_tracker.py` — add `pipeline_name`, `agents_used`, `extra_metadata` parameters to start_run/complete_run
- [ ] 4. Migrate `backend/app/routes/swarms.py` — replace save_pipeline_run with run_tracker calls
- [ ] 5. Migrate `backend/app/routes/enterprise_ops.py`, `document_intelligence.py`, `analyze.py`, `drive_pipeline.py`, `portfolio_copilot.py` — same pattern
- [ ] 6. Simplify `backend/app/routes/workflow_runs.py` — _get_db_runs and _get_db_health read from workflow_runs ONLY

## Phase 2: UX Fixes (Tasks 7-10)

- [ ] 7. Fix "Ejecutar" button in 5 typed dashboards — do NOT navigate away, poll + update stats inline
- [ ] 8. Dashboard Ejecuciones Recientes — verify pagination (10/page), scroll (max 400px), Clear All button work after deploy
- [ ] 9. Retry and Fallback counters — compute from step_executions.retry_count and provider/model fields
- [ ] 10. Verify cost tracking chain: LLM → AgentResult → step_executions → workflow_runs → KPI display

## Phase 3: Wizard Intelligence (Tasks 11-12)

- [ ] 11. "Crear automatización con esto" → save demo result to localStorage → Wizard reads and pre-fills type, name, description, input, output
- [ ] 12. Wizard type selection pre-fills name and description (not just input/output) using QUICK_TYPE_DEFAULTS pattern

## Verification

After all tasks:
- [ ] Run an automation → verify it appears in: automation dashboard stats, Dashboard KPIs, Ejecuciones list, Métricas tab, Agent Activity
- [ ] Run a swarm → verify same 7 reflection points
- [ ] Run Enterprise Ops from Intelligence Hub → verify it appears in Dashboard + Ejecuciones
- [ ] Verify pipeline_runs table receives NO new inserts
- [ ] Verify 260/260 tests pass
