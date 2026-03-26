CREATE TABLE IF NOT EXISTS cost_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES workflow_runs(id),
    step_name VARCHAR(100),
    agent_type VARCHAR(50),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    tokens_input INT DEFAULT 0,
    tokens_output INT DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_cost_run ON cost_events(run_id);
CREATE INDEX idx_cost_created ON cost_events(created_at DESC);
