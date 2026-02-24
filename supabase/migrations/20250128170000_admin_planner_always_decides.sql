-- Add planner_always_decides to admin_orchestration_settings.
-- When true, every user turn goes to the planner LLM to decide next action; intent is only context.
-- When false (default), intent's recommended_next_action can directly set the next step.

BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'admin_orchestration_settings' AND column_name = 'planner_always_decides'
  ) THEN
    ALTER TABLE admin_orchestration_settings ADD COLUMN planner_always_decides BOOLEAN DEFAULT false;
    COMMENT ON COLUMN admin_orchestration_settings.planner_always_decides IS 'When true, planner LLM decides every next action; no hardcoded intent rules';
  END IF;
END $$;

COMMIT;
