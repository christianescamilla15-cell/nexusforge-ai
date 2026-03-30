CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running','completed','failed')),
    trigger_source VARCHAR(20) DEFAULT 'serverless' CHECK (trigger_source IN ('serverless','backend','cli')),
    input_summary JSONB DEFAULT '{}',
    output_summary JSONB DEFAULT '{}',
    steps JSONB DEFAULT '[]',
    file_name VARCHAR(500),
    document_type VARCHAR(100),
    total_tokens INT DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    processing_time_ms INT,
    llm_used BOOLEAN DEFAULT false,
    agents_used JSONB DEFAULT '[]',
    notion_url TEXT,
    webhook_sent BOOLEAN DEFAULT false,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_pipeline_runs_name ON pipeline_runs(pipeline_name);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_created ON pipeline_runs(created_at DESC);
