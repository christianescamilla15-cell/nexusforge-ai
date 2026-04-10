-- Batch 3 deliverable F5 — persistent showcase runs
--
-- Stores snapshots of the showcase pipeline (ingestion + analyzers +
-- strangler planner + compliance profile) per tenant. One row per run;
-- the /api/refactor/showcase/* read endpoints prefer the latest row
-- for a given tenant_slug and fall back to static JSON fixtures when
-- nothing has been persisted yet.
--
-- tenant_slug is a plain string so pipelines can run against synthetic
-- or demo tenants before an organization record exists. If/when an
-- organizations row is present with the same slug, the application
-- joins them at read time; there is no hard foreign key here on
-- purpose — it would otherwise block standalone showcase demos.

CREATE TABLE IF NOT EXISTS showcase_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_slug VARCHAR(100) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    report JSONB NOT NULL,
    compliance JSONB,
    strangler_plans JSONB NOT NULL DEFAULT '{}'::jsonb,
    duration_ms INT NOT NULL DEFAULT 0,
    source VARCHAR(20) NOT NULL DEFAULT 'pipeline',
    created_by UUID REFERENCES nf_users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Fast "latest run per tenant" lookup
CREATE INDEX IF NOT EXISTS idx_showcase_runs_tenant_latest
    ON showcase_runs (tenant_slug, generated_at DESC);

-- Audit / history queries
CREATE INDEX IF NOT EXISTS idx_showcase_runs_created_by
    ON showcase_runs (created_by)
    WHERE created_by IS NOT NULL;
