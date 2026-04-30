-- SUPERSEDED 2026-04-30 (see 036_audit_log_consolidate.sql).
--
-- This migration originally created `audit_log` with a
-- non-canonical schema (BIGSERIAL id, no user_id, no token/cost
-- columns) that conflicts with `app/auth/audit.log_action()`.
-- Migration 013 then re-declared the table with the correct
-- schema, but its `IF NOT EXISTS` guard turned 013 into a no-op
-- on deploys that had already run 010.
--
-- Migration 036 reconciles the two schemas by ALTERing audit_log
-- additively. This file is left in place (rather than deleted)
-- so the migrations history stays linear for any deploy that has
-- already recorded 010 as applied.

-- Idempotent recreation of the canonical schema for fresh deploys
-- that never ran any audit_log migration before.
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(30),
    resource_id VARCHAR(100),
    details JSONB DEFAULT '{}',
    ip_address VARCHAR(45),
    tokens_used INT DEFAULT 0,
    cost_usd NUMERIC(10,6) DEFAULT 0,
    duration_ms INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource_type, resource_id);
