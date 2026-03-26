CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','queued','running','completed','failed','cancelled')),
    trigger_type VARCHAR(20) DEFAULT 'manual' CHECK (trigger_type IN ('manual','schedule','webhook','event')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    total_tokens INT DEFAULT 0,
    total_cost_usd DECIMAL(10,6) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_runs_workflow ON workflow_runs(workflow_id);
CREATE INDEX idx_runs_status ON workflow_runs(status);
CREATE INDEX idx_runs_created ON workflow_runs(created_at DESC);
