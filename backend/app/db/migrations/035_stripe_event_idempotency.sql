-- Sprint 1 / C-5 (2026-04-25) — Stripe webhook idempotency table.
--
-- Stripe guarantees at-least-once delivery, not exactly-once: a single
-- event may arrive multiple times after a network blip or a webhook
-- retry from Stripe's side. Without idempotency tracking, NexusForge
-- would re-apply `checkout.session.completed` on every retry — letting
-- an attacker who captures a webhook payload replay it indefinitely.
--
-- This table records every `event["id"]` we have already processed.
-- The webhook handler `INSERT ... ON CONFLICT DO NOTHING`s on each
-- event; if the insert reports `0` rows affected, the event has been
-- handled before and the handler returns 200 without re-running side
-- effects.
--
-- Retention: 30 days is sufficient — Stripe retries within minutes,
-- not days. A scheduled job can prune older rows; not in scope here.

CREATE TABLE IF NOT EXISTS processed_stripe_events (
    event_id VARCHAR(255) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- For pruning by age.
CREATE INDEX IF NOT EXISTS idx_processed_stripe_events_received_at
    ON processed_stripe_events (received_at);
