-- Migration: Admin Command Center (Module 18) - support escalations assign by clerk
-- Allow assigning escalations to platform admins by clerk_user_id when user_id is null

BEGIN;

ALTER TABLE support_escalations ADD COLUMN IF NOT EXISTS assigned_to_clerk_id TEXT;

COMMENT ON COLUMN support_escalations.assigned_to_clerk_id IS 'Clerk user ID when assigned to admin without users.id';

ALTER TABLE support_escalations ALTER COLUMN assigned_to DROP NOT NULL;

COMMIT;
