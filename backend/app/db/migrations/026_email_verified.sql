-- Email verification flag
ALTER TABLE nf_users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT false;
