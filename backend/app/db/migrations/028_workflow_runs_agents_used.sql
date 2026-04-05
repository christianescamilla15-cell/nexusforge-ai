-- Migration 028: Extend workflow_runs as unified polymorphic execution table
-- Replaces pipeline_runs as the single source of truth for ALL executions
-- Pattern: n8n unified workflow_execution + Temporal namespace

-- Core polymorphic columns
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS pipeline_name VARCHAR(100) DEFAULT NULL;
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS agents_used JSONB DEFAULT '[]';
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS execution_type VARCHAR(30) DEFAULT 'dag_workflow';
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS automation_id UUID;
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS trigger_source VARCHAR(50);
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS input_data JSONB;
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS output_data JSONB;
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS user_id UUID;

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_runs_execution_type ON workflow_runs(execution_type);
CREATE INDEX IF NOT EXISTS idx_runs_automation ON workflow_runs(automation_id);
CREATE INDEX IF NOT EXISTS idx_runs_pipeline_name ON workflow_runs(pipeline_name);
CREATE INDEX IF NOT EXISTS idx_runs_user_id ON workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON workflow_runs(started_at DESC);

-- Mark pipeline_runs as legacy
COMMENT ON TABLE pipeline_runs IS 'LEGACY: No longer written to. All new executions go to workflow_runs. Kept for historical data only.';
