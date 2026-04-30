-- 036: consolidate the `audit_log` (singular) schema (2026-04-30).
--
-- Two earlier migrations both ran `CREATE TABLE IF NOT EXISTS
-- audit_log (...)` with INCOMPATIBLE schemas:
--
--   010_audit_log.sql  (BIGSERIAL id; NO user_id; no tokens/cost/duration)
--   013_api_keys_audit_custom_agents.sql  (UUID id; user_id; tokens/cost/duration)
--
-- Whichever migration ran first won; the other became a silent no-op
-- because of the IF NOT EXISTS guard. Deploys that ran 010 first end
-- up with a table that lacks `user_id` — every INSERT from
-- `app/auth/audit.log_action()` fails because the column doesn't
-- exist, and every read in the activity-log endpoint returns nothing
-- meaningful.
--
-- This migration brings any audit_log table into line with the
-- canonical (013) schema by ADDing whatever columns are missing,
-- idempotently. Existing rows are preserved.

-- Add the canonical columns (no-op when the column already exists,
-- which is the case on deploys that ran 013 first).
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS tokens_used INT DEFAULT 0;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS cost_usd NUMERIC(10,6) DEFAULT 0;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS duration_ms INT DEFAULT 0;

-- Indexes: created idempotently. The 013 migration already declares
-- these but only fired on fresh deploys.
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
