-- Multi-tenant: organizations + roles + tenant_id
-- NexusForge 2.0 SaaS foundation

-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(20) DEFAULT 'free',
    stripe_customer_id VARCHAR(100),
    stripe_subscription_id VARCHAR(100),
    max_seats INT DEFAULT 5,
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Organization membership (user ↔ org)
CREATE TABLE IF NOT EXISTS organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES nf_users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member',  -- owner, admin, member, viewer
    invited_by UUID REFERENCES nf_users(id),
    joined_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, user_id)
);

-- Add org_id to core tables (nullable for backward compat)
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
ALTER TABLE automations ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
ALTER TABLE connectors ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Indexes for tenant queries
CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(org_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);
CREATE INDEX IF NOT EXISTS idx_workflows_org ON workflows(org_id);
CREATE INDEX IF NOT EXISTS idx_automations_org ON automations(org_id);
CREATE INDEX IF NOT EXISTS idx_runs_org ON workflow_runs(org_id);
CREATE INDEX IF NOT EXISTS idx_agent_configs_org ON agent_configs(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_org ON audit_logs(org_id);

-- Row-Level Security policies
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE automations ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- RLS policies: users can only see rows in their org.
-- Note: app connects as 'nexusforge_app' role, sets current_setting('app.org_id').
--
-- PostgreSQL does NOT support `CREATE POLICY IF NOT EXISTS` (it is the
-- one CREATE statement missing that clause, even in PG 16). We wrap
-- each CREATE in a DO block that checks pg_policies first, so the
-- migration stays idempotent and re-running it is safe.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'workflows'
          AND policyname = 'org_isolation_workflows'
    ) THEN
        CREATE POLICY org_isolation_workflows ON workflows
            USING (org_id IS NULL OR org_id = current_setting('app.org_id', true)::uuid);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'automations'
          AND policyname = 'org_isolation_automations'
    ) THEN
        CREATE POLICY org_isolation_automations ON automations
            USING (org_id IS NULL OR org_id = current_setting('app.org_id', true)::uuid);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'workflow_runs'
          AND policyname = 'org_isolation_runs'
    ) THEN
        CREATE POLICY org_isolation_runs ON workflow_runs
            USING (org_id IS NULL OR org_id = current_setting('app.org_id', true)::uuid);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'agent_configs'
          AND policyname = 'org_isolation_configs'
    ) THEN
        CREATE POLICY org_isolation_configs ON agent_configs
            USING (org_id IS NULL OR org_id = current_setting('app.org_id', true)::uuid);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'documents'
          AND policyname = 'org_isolation_documents'
    ) THEN
        CREATE POLICY org_isolation_documents ON documents
            USING (org_id IS NULL OR org_id = current_setting('app.org_id', true)::uuid);
    END IF;
END $$;
