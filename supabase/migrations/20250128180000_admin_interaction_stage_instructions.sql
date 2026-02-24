-- Add interaction-stage instructions for Opening vs Narrowing.
-- Opening: first touch — model is more excited, suggests experiences we offer.
-- Narrowing: follow-up — engage to narrow down the plan, accommodate changes.

BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'admin_orchestration_settings' AND column_name = 'opening_instructions'
  ) THEN
    ALTER TABLE admin_orchestration_settings ADD COLUMN opening_instructions TEXT;
    COMMENT ON COLUMN admin_orchestration_settings.opening_instructions IS 'When interaction_stage=opening: inject into planner/engagement (e.g. be excited, suggest experiences we offer)';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'admin_orchestration_settings' AND column_name = 'narrowing_instructions'
  ) THEN
    ALTER TABLE admin_orchestration_settings ADD COLUMN narrowing_instructions TEXT;
    COMMENT ON COLUMN admin_orchestration_settings.narrowing_instructions IS 'When interaction_stage=narrowing: inject (e.g. engage to narrow down, accommodate changes)';
  END IF;
END $$;

COMMIT;
