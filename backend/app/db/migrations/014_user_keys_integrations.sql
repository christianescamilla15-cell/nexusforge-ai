-- 014: User API keys for LLM providers and integrations

CREATE TABLE IF NOT EXISTS user_provider_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES nf_users(id) ON DELETE CASCADE,
    provider VARCHAR(30) NOT NULL,  -- groq, claude, openai, openai-gpt4o
    api_key_encrypted VARCHAR(500) NOT NULL,  -- stored encrypted (for now, plain — encrypt later)
    model VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, provider)
);

CREATE TABLE IF NOT EXISTS user_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES nf_users(id) ON DELETE CASCADE,
    service VARCHAR(30) NOT NULL,  -- email, gmail, drive, notion, slack, webhook, whatsapp, calendar
    config JSONB DEFAULT '{}',     -- service-specific config (keys, URLs, IDs)
    is_active BOOLEAN DEFAULT true,
    last_tested_at TIMESTAMPTZ,
    test_status VARCHAR(20) DEFAULT 'untested',  -- untested, ok, failed
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, service)
);

CREATE INDEX IF NOT EXISTS idx_user_keys_user ON user_provider_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_integrations_user ON user_integrations(user_id);
