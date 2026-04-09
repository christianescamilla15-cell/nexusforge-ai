-- Data retention policies + auto-archive support
-- Prevents unbounded DB growth (Aeromexico: 15-20% monthly growth)

-- Archive tables for old data
CREATE TABLE IF NOT EXISTS workflow_runs_archive (
    LIKE workflow_runs INCLUDING ALL
);

CREATE TABLE IF NOT EXISTS step_executions_archive (
    LIKE step_executions INCLUDING ALL
);

CREATE TABLE IF NOT EXISTS audit_logs_archive (
    LIKE audit_logs INCLUDING ALL
);

-- Retention policy tracking
CREATE TABLE IF NOT EXISTS retention_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL UNIQUE,
    retention_days INT NOT NULL DEFAULT 90,
    archive_enabled BOOLEAN DEFAULT true,
    last_archived_at TIMESTAMPTZ,
    rows_archived BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Default policies
INSERT INTO retention_policies (table_name, retention_days, archive_enabled) VALUES
    ('workflow_runs', 90, true),
    ('step_executions', 60, true),
    ('audit_logs', 365, true),
    ('dead_letters', 30, false),
    ('cost_events', 180, true),
    ('auth_codes', 1, false)
ON CONFLICT (table_name) DO NOTHING;

-- Reset daily counters for API keys
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS requests_today INT DEFAULT 0;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS requests_reset_date DATE;

-- Index for archive queries
CREATE INDEX IF NOT EXISTS idx_runs_created_archive ON workflow_runs(created_at) WHERE status IN ('completed', 'failed');
CREATE INDEX IF NOT EXISTS idx_steps_created_archive ON step_executions(completed_at);
CREATE INDEX IF NOT EXISTS idx_audit_created_archive ON audit_logs(created_at);
