CREATE TABLE IF NOT EXISTS dead_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES workflow_runs(id),
    step_name VARCHAR(100),
    payload JSONB,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX idx_dead_unresolved ON dead_letters(resolved) WHERE resolved = false;
