-- Migration: Platform config (commission rates, feature flags)
-- Date: 2024-01-28
-- Dependencies: partner_portal_production

BEGIN;

-- Platform config (single row)
CREATE TABLE IF NOT EXISTS platform_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  commission_rate_pct DECIMAL(5,2) DEFAULT 10.00,
  discovery_relevance_threshold DECIMAL(5,2) DEFAULT 0.70,
  enable_self_registration BOOLEAN DEFAULT TRUE,
  enable_chatgpt BOOLEAN DEFAULT TRUE,
  feature_flags JSONB DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default config if empty
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM platform_config LIMIT 1) THEN
    INSERT INTO platform_config (commission_rate_pct, discovery_relevance_threshold, enable_self_registration, enable_chatgpt)
    VALUES (10.00, 0.70, TRUE, TRUE);
  END IF;
END $$;

-- Allow platform_admins to store Clerk user ID for auth (users table may not be synced)
ALTER TABLE platform_admins ADD COLUMN IF NOT EXISTS clerk_user_id TEXT UNIQUE;
ALTER TABLE platform_admins ALTER COLUMN user_id DROP NOT NULL;

COMMIT;
