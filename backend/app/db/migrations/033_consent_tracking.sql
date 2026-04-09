-- Consent tracking (GDPR/LFPDPPP compliance)
CREATE TABLE IF NOT EXISTS user_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES nf_users(id) ON DELETE CASCADE,
    consent_type VARCHAR(50) NOT NULL,   -- terms_of_service, privacy_policy, marketing, data_processing
    accepted BOOLEAN NOT NULL,
    version VARCHAR(20) DEFAULT '1.0',   -- T&C version accepted
    ip_address VARCHAR(45),
    user_agent TEXT,
    accepted_at TIMESTAMPTZ DEFAULT now(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_consents_user ON user_consents(user_id);
CREATE INDEX IF NOT EXISTS idx_consents_type ON user_consents(consent_type, accepted);

-- Onboarding tracking
ALTER TABLE nf_users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT false;
ALTER TABLE nf_users ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMPTZ;
