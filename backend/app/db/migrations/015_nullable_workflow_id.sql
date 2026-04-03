-- Allow workflow_runs without a saved workflow (for use-case executions)
ALTER TABLE workflow_runs ALTER COLUMN workflow_id DROP NOT NULL;
ALTER TABLE workflow_runs DROP CONSTRAINT IF EXISTS workflow_runs_workflow_id_fkey;
