-- 016: Per-user agent configuration

CREATE TABLE IF NOT EXISTS agent_configs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES nf_users(id) ON DELETE CASCADE,
    agent_type   VARCHAR(50) NOT NULL,
    provider     VARCHAR(30) DEFAULT 'groq',
    model        VARCHAR(100) DEFAULT 'llama-3.3-70b-versatile',
    temperature  DECIMAL(3,2) DEFAULT 0.3,
    max_tokens   INT DEFAULT 1024,
    system_prompt TEXT,
    tools        JSONB DEFAULT '[]',
    status       VARCHAR(20) DEFAULT 'active',
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, agent_type)
);

CREATE INDEX IF NOT EXISTS idx_agent_configs_user ON agent_configs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_configs_type ON agent_configs(agent_type);
