-- Migration: Link Account support (Pillar 6 - Zero-Friction Auth)
-- Map Clerk identity to platform user for account_links
BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS clerk_user_id TEXT UNIQUE;
CREATE INDEX IF NOT EXISTS idx_users_clerk_user_id ON users(clerk_user_id) WHERE clerk_user_id IS NOT NULL;

COMMIT;
