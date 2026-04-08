# Tasks: Unify Execution Tracking

## Phase 1: Database Migration (Tasks 1-6)

- [x] 1. Audit all `save_pipeline_run()` calls — RESULT: zero active calls, all migrated to run_tracker
- [x] 2. Create migration `028_workflow_runs_agents_used.sql` — DONE (adds agents_used, pipeline_name, execution_type, etc.)
- [x] 3. Extend `backend/app/utils/run_tracker.py` — DONE (start_run, record_step, complete_run with all params)
- [x] 4. Migrate swarms.py — DONE (uses run_tracker)
- [x] 5. Migrate enterprise_ops.py, document_intelligence.py, analyze.py, drive_pipeline.py, portfolio_copilot.py — DONE (all 5 use run_tracker)
- [x] 6. Simplify workflow_runs.py — DONE (_get_db_runs and _get_db_health read from workflow_runs ONLY)

## Phase 2: UX Fixes (Tasks 7-10)

- [x] 7. Fix "Ejecutar" button — DONE (all 5 dashboards execute in-place, no navigation)
- [x] 8. Dashboard pagination — DONE (PAGE_SIZE=10, maxHeight 400px, Clear All button)
- [x] 9. Retry/fallback counters — DONE (CostTokenDashboard shows retries + fallbacks per agent)
- [x] 10. Cost tracking chain — DONE (LLM → AgentResult → step_executions → workflow_runs → KPI verified)

## Phase 3: Wizard Intelligence (Tasks 11-12)

- [x] 11. "Crear automatización con esto" → DONE (localStorage nxf_wizard_prefill → WizardPage reads on mount)
- [x] 12. Wizard type selection pre-fills name/description — DONE (QUICK_TYPE_DEFAULTS with name + desc in en/es)

## Verification

- [x] pipeline_runs table receives NO new inserts (verified: 0 references to save_pipeline_run in routes)
- [x] 6 routes use run_tracker (analyze, document_intelligence, drive_pipeline, enterprise_ops, portfolio_copilot, swarms)
- [x] 296/296 tests pass
- [ ] End-to-end: Run automation → verify appears in all 9 reflection points (requires live environment)
- [ ] End-to-end: Run swarm → verify appears in all 7 reflection points (requires live environment)
