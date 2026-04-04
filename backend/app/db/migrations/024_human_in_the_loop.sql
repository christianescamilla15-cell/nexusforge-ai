-- Human-in-the-loop: approval workflow for automations
-- requires_approval: when true, automation pauses before final action
-- approval_status: tracks review state for each result

ALTER TABLE automations ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN DEFAULT false;

ALTER TABLE automation_results ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) DEFAULT 'auto';
-- Values: auto = no approval needed, pending = waiting, approved = sent, rejected = not sent

CREATE INDEX IF NOT EXISTS idx_results_approval ON automation_results(approval_status)
    WHERE approval_status = 'pending';
