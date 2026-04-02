-- 013: API Keys, Audit Trail, Custom Agents, Slack integration

-- ─── API KEYS ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES nf_users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    key_prefix VARCHAR(12) NOT NULL,  -- first 8 chars for identification (nf_xxxxx...)
    name VARCHAR(100) DEFAULT 'Default',
    scopes TEXT[] DEFAULT ARRAY['execute', 'read'],
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    requests_today INT DEFAULT 0,
    requests_reset_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

-- ─── AUDIT TRAIL ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES nf_users(id),
    action VARCHAR(50) NOT NULL,  -- workflow.execute, agent.run, document.upload, auth.login, etc.
    resource_type VARCHAR(30),    -- workflow, agent, document, user
    resource_id VARCHAR(100),
    details JSONB DEFAULT '{}',
    ip_address VARCHAR(45),
    tokens_used INT DEFAULT 0,
    cost_usd NUMERIC(10,6) DEFAULT 0,
    duration_ms INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);

-- ─── CUSTOM AGENTS ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS custom_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES nf_users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    agent_type VARCHAR(50) DEFAULT 'custom',
    system_prompt TEXT NOT NULL,
    model VARCHAR(50) DEFAULT 'llama-3.3-70b-versatile',
    provider VARCHAR(20) DEFAULT 'groq',
    temperature NUMERIC(3,2) DEFAULT 0.3,
    max_tokens INT DEFAULT 1024,
    tools JSONB DEFAULT '[]',
    is_public BOOLEAN DEFAULT false,
    executions INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_custom_agents_user ON custom_agents(user_id);

-- ─── SLACK INTEGRATIONS ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS slack_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES nf_users(id) ON DELETE CASCADE,
    webhook_url VARCHAR(500) NOT NULL,
    channel_name VARCHAR(100),
    notify_on TEXT[] DEFAULT ARRAY['workflow.completed', 'workflow.failed'],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_slack_user ON slack_integrations(user_id);
