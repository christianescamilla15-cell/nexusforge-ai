-- workflow_runs — execution table for workflow runs.
--
-- HISTORICAL CONFLICT (resolved 2026-05-10): an earlier observability
-- migration (`001_observability.sql`) ALSO creates `workflow_runs` but
-- with a different column set (workflow_name TEXT instead of
-- workflow_id UUID, no trigger_type, no metadata). Because both files
-- use `CREATE TABLE IF NOT EXISTS`, 001 wins on a fresh DB and 002's
-- table-create is a no-op. The original 002 then crashed on
-- `CREATE INDEX ... ON workflow_runs(workflow_id)` because the column
-- didn't exist. The migrator marked 002 as failed and skipped 015
-- in cascade, leaving /api/executions/ broken in EVERY environment
-- that applied both migrations.
--
-- Triangulation pass on 2026-05-10 surfaced this: 35 of 37
-- migrations applied, but the application code expects the 002 schema
-- and crashed with "column workflow_id does not exist" on first hit.
--
-- THIS REWRITE makes 002 idempotent and additive:
--   - The CREATE TABLE keeps the 002 shape for fresh DBs.
--   - The ALTER TABLE ADD COLUMN IF NOT EXISTS lines reconcile a
--     001-shaped table to the fields executions.py needs.
--   - workflow_id is added as NULLABLE without FK (mirrors the
--     end-state that 015 enforces anyway). Both migrations now reach
--     the same final schema regardless of execution order.

CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID,
    status VARCHAR(20) DEFAULT 'pending',
    trigger_type VARCHAR(20) DEFAULT 'manual',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    total_tokens INT DEFAULT 0,
    total_cost_usd DECIMAL(10,6) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Reconcile with the 001_observability table shape.
-- Each ADD COLUMN IF NOT EXISTS is a no-op when 002 already created
-- the table fresh, and an additive merge when 001 already created the
-- wider observability shape (which is missing these specific columns).
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS workflow_id   UUID;
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS trigger_type  VARCHAR(20) DEFAULT 'manual';
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS completed_at  TIMESTAMPTZ;
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS metadata      JSONB DEFAULT '{}';

-- 001_observability declared workflow_name, topology, and status as
-- NOT NULL (the observability path always knew those values). The
-- executions/automations path doesn't have them — `executions.py`
-- only provides (workflow_id, status, trigger_type, metadata,
-- user_id, execution_type). Without dropping NOT NULL here, the
-- executions INSERT crashes with NotNullViolationError on
-- workflow_name. Use a DO block so the migration is safe even on a
-- fresh DB that never ran 001 (those columns won't exist there;
-- DROP NOT NULL would otherwise raise).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'workflow_runs' AND column_name = 'workflow_name') THEN
        ALTER TABLE workflow_runs ALTER COLUMN workflow_name DROP NOT NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'workflow_runs' AND column_name = 'topology') THEN
        ALTER TABLE workflow_runs ALTER COLUMN topology DROP NOT NULL;
    END IF;
    -- status was NOT NULL in 001; 002 provides a default, but legacy
    -- INSERTs that omit status entirely would fail without this.
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'workflow_runs' AND column_name = 'status') THEN
        ALTER TABLE workflow_runs ALTER COLUMN status DROP NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_runs_workflow ON workflow_runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_runs_status   ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created  ON workflow_runs(created_at DESC);
