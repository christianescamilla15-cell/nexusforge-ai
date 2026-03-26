CREATE TABLE IF NOT EXISTS agent_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    config JSONB DEFAULT '{}',
    system_prompt TEXT,
    tools TEXT[] DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','paused','deprecated')),
    created_at TIMESTAMPTZ DEFAULT now()
);
