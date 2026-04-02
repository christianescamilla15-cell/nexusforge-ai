-- 012: Users table for authentication and multi-tenancy

CREATE TABLE IF NOT EXISTS nf_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(150),
    password_hash VARCHAR(255),  -- NULL for OAuth-only users
    provider VARCHAR(20) DEFAULT 'email' CHECK (provider IN ('email', 'google', 'github')),
    provider_id VARCHAR(255),     -- OAuth provider user ID
    role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('admin', 'owner', 'member', 'viewer')),
    plan VARCHAR(20) DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'team', 'enterprise')),
    runs_today INT DEFAULT 0,
    runs_reset_date DATE DEFAULT CURRENT_DATE,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_nf_users_email ON nf_users(email);
CREATE INDEX IF NOT EXISTS idx_nf_users_provider ON nf_users(provider, provider_id);

-- Add user_id to pipeline_runs for multi-tenancy
DO $$ BEGIN
    ALTER TABLE pipeline_runs ADD COLUMN user_id UUID REFERENCES nf_users(id);
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user ON pipeline_runs(user_id);

-- Add 'frontend' to trigger_source check (for future use)
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS pipeline_runs_trigger_source_check;
ALTER TABLE pipeline_runs ADD CONSTRAINT pipeline_runs_trigger_source_check
    CHECK (trigger_source IN ('serverless', 'backend', 'cli', 'frontend', 'api'));
