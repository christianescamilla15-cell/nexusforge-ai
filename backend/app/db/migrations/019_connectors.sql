CREATE TABLE IF NOT EXISTS connectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    connector_type VARCHAR(30) NOT NULL,
    name VARCHAR(100) NOT NULL,
    config JSONB DEFAULT '{}',
    field_mapping JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    last_test_at TIMESTAMPTZ,
    last_test_status VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_connectors_user ON connectors(user_id);
CREATE INDEX IF NOT EXISTS idx_connectors_type ON connectors(connector_type);

CREATE TABLE IF NOT EXISTS automation_connectors (
    automation_id UUID REFERENCES automations(id) ON DELETE CASCADE,
    connector_id UUID REFERENCES connectors(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'input',
    PRIMARY KEY (automation_id, connector_id)
);
