-- Migration: Add ucp_prioritized to admin_orchestration_settings (for existing deployments)
-- Ensures column exists when table was created before ucp_prioritized was added
-- Date: 2025-01-28

BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'admin_orchestration_settings' AND column_name = 'ucp_prioritized'
  ) THEN
    ALTER TABLE admin_orchestration_settings ADD COLUMN ucp_prioritized BOOLEAN DEFAULT false;
    COMMENT ON COLUMN admin_orchestration_settings.ucp_prioritized IS 'When true, planner calls fetch_ucp_manifest first before discovery';
  END IF;
END $$;

COMMIT;
