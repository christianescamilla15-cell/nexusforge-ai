-- Migration 030: Per-automation output destination config
-- Stores which integrations each automation sends results to
-- Example: {"email": true, "notion": true, "slack": false, "drive": false, "webhook": false}

ALTER TABLE automations ADD COLUMN IF NOT EXISTS output_config JSONB DEFAULT '{}';
