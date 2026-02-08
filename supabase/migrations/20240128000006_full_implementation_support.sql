-- Migration: Full implementation support (no simulator)
-- Adds original_request to negotiations, stripe_account_id to partners

BEGIN;

-- Add original_request to negotiations for change request payload
ALTER TABLE negotiations ADD COLUMN IF NOT EXISTS original_request JSONB;

-- Add stripe_account_id to partners for Stripe Connect
ALTER TABLE partners ADD COLUMN IF NOT EXISTS stripe_account_id TEXT;

COMMIT;
