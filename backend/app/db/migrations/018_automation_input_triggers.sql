-- 018: Automation input config, webhook secret, and schedule next_run_at

ALTER TABLE automations
    ADD COLUMN IF NOT EXISTS input_config JSONB DEFAULT '{"type": "none"}',
    ADD COLUMN IF NOT EXISTS webhook_secret VARCHAR(100),
    ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ;

-- Index for webhook lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_automations_webhook_secret
    ON automations(webhook_secret) WHERE webhook_secret IS NOT NULL;

-- Index for scheduler polling
CREATE INDEX IF NOT EXISTS idx_automations_next_run
    ON automations(next_run_at) WHERE trigger_type = 'schedule' AND is_active = true;
