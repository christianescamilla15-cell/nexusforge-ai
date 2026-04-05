-- Migration 029: Counter projections for instant KPIs
-- Pattern: ClickHouse materialized view + PostgreSQL pg_ivm
-- Reads are O(1) instead of COUNT(*) full table scan

CREATE TABLE IF NOT EXISTS user_execution_stats (
    user_id UUID PRIMARY KEY,
    total_runs INTEGER DEFAULT 0,
    runs_completed INTEGER DEFAULT 0,
    runs_failed INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd NUMERIC(12,6) DEFAULT 0,
    last_run_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Trigger function: auto-updates stats on every INSERT into workflow_runs
CREATE OR REPLACE FUNCTION update_execution_stats() RETURNS TRIGGER AS $$
BEGIN
    -- Only track if user_id is set
    IF NEW.user_id IS NOT NULL THEN
        INSERT INTO user_execution_stats (user_id, total_runs, runs_completed, runs_failed, total_tokens, total_cost_usd, last_run_at)
        VALUES (
            NEW.user_id, 1,
            CASE WHEN NEW.status = 'completed' THEN 1 ELSE 0 END,
            CASE WHEN NEW.status = 'failed' THEN 1 ELSE 0 END,
            COALESCE(NEW.total_tokens, 0),
            COALESCE(NEW.total_cost_usd, 0),
            NEW.started_at
        )
        ON CONFLICT (user_id) DO UPDATE SET
            total_runs = user_execution_stats.total_runs + 1,
            runs_completed = user_execution_stats.runs_completed + EXCLUDED.runs_completed,
            runs_failed = user_execution_stats.runs_failed + EXCLUDED.runs_failed,
            total_tokens = user_execution_stats.total_tokens + EXCLUDED.total_tokens,
            total_cost_usd = user_execution_stats.total_cost_usd + EXCLUDED.total_cost_usd,
            last_run_at = GREATEST(user_execution_stats.last_run_at, EXCLUDED.last_run_at),
            updated_at = now();
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

-- Also update stats when a run completes (status changes from running→completed/failed)
CREATE OR REPLACE FUNCTION update_execution_stats_on_complete() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_id IS NOT NULL AND OLD.status = 'running' AND NEW.status IN ('completed', 'failed') THEN
        UPDATE user_execution_stats SET
            runs_completed = runs_completed + CASE WHEN NEW.status = 'completed' THEN 1 ELSE 0 END,
            runs_failed = runs_failed + CASE WHEN NEW.status = 'failed' THEN 1 ELSE 0 END,
            total_tokens = total_tokens + COALESCE(NEW.total_tokens, 0) - COALESCE(OLD.total_tokens, 0),
            total_cost_usd = total_cost_usd + COALESCE(NEW.total_cost_usd, 0) - COALESCE(OLD.total_cost_usd, 0),
            updated_at = now()
        WHERE user_id = NEW.user_id;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;

-- Trigger on INSERT (run starts — counts total_runs)
DROP TRIGGER IF EXISTS trg_execution_stats_insert ON workflow_runs;
CREATE TRIGGER trg_execution_stats_insert AFTER INSERT ON workflow_runs
FOR EACH ROW EXECUTE FUNCTION update_execution_stats();

-- Trigger on UPDATE (run completes — counts completed/failed + tokens/cost)
DROP TRIGGER IF EXISTS trg_execution_stats_update ON workflow_runs;
CREATE TRIGGER trg_execution_stats_update AFTER UPDATE ON workflow_runs
FOR EACH ROW EXECUTE FUNCTION update_execution_stats_on_complete();
