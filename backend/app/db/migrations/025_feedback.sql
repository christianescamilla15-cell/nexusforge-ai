-- Persistent feedback storage (was in-memory, lost on restart)
CREATE TABLE IF NOT EXISTS run_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,
    user_id UUID,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    approved BOOLEAN DEFAULT NULL,
    comments TEXT DEFAULT '',
    agent_type VARCHAR(50) DEFAULT '',
    workflow_type VARCHAR(50) DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_run_feedback_run_id ON run_feedback(run_id);
CREATE INDEX IF NOT EXISTS idx_run_feedback_agent ON run_feedback(agent_type);
CREATE INDEX IF NOT EXISTS idx_run_feedback_created ON run_feedback(created_at DESC);
