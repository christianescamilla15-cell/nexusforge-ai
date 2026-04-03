-- 017: User-published automations

CREATE TABLE IF NOT EXISTS automations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES nf_users(id) ON DELETE CASCADE,
    workflow_id     UUID REFERENCES workflows(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    icon            VARCHAR(10) DEFAULT '⚡',
    color           VARCHAR(20) DEFAULT '#6366F1',
    trigger_type    VARCHAR(20) DEFAULT 'manual'
                        CHECK (trigger_type IN ('manual', 'schedule', 'webhook')),
    schedule_cron   VARCHAR(50),
    webhook_secret  VARCHAR(100),
    is_active       BOOLEAN DEFAULT true,
    total_runs      INT DEFAULT 0,
    last_run_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_automations_user ON automations(user_id);
CREATE INDEX IF NOT EXISTS idx_automations_workflow ON automations(workflow_id);
