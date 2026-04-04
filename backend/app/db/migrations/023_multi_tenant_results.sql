-- Multi-tenant: add user_id to core tables
-- Results persistence: automation_results table

-- 1. Add user_id to workflows
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS user_id UUID;

-- 2. Add user_id to workflow_runs
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS user_id UUID;

-- 3. Add user_id to documents
ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id UUID;

-- 4. Create automation_results table for persistent outputs
CREATE TABLE IF NOT EXISTS automation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id UUID REFERENCES automations(id) ON DELETE CASCADE,
    user_id UUID,
    run_id UUID REFERENCES workflow_runs(id) ON DELETE SET NULL,
    input_type VARCHAR(20) DEFAULT 'text',
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'completed',
    processing_time_ms INT DEFAULT 0,
    tokens_used INT DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_results_automation ON automation_results(automation_id);
CREATE INDEX IF NOT EXISTS idx_results_user ON automation_results(user_id);
CREATE INDEX IF NOT EXISTS idx_results_created ON automation_results(created_at DESC);

-- 5. Dashboard widget configs per automation
CREATE TABLE IF NOT EXISTS automation_widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id UUID REFERENCES automations(id) ON DELETE CASCADE,
    widget_type VARCHAR(30) NOT NULL,
    position INT DEFAULT 0,
    width INT DEFAULT 6,
    height INT DEFAULT 4,
    config JSONB DEFAULT '{}',
    is_visible BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_widgets_automation ON automation_widgets(automation_id);
