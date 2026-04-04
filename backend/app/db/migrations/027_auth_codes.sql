-- Auth codes table: replaces in-memory _verify_codes and _reset_codes dicts
-- Shared across workers, survives restarts, auto-expires
CREATE TABLE IF NOT EXISTS auth_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    code VARCHAR(6) NOT NULL,
    purpose VARCHAR(20) NOT NULL,  -- 'verify' or 'reset'
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_codes_email ON auth_codes(email, purpose);
CREATE INDEX IF NOT EXISTS idx_auth_codes_expires ON auth_codes(expires_at);

-- Cleanup: auto-delete expired codes older than 1 hour
-- (run manually or via scheduled task)
