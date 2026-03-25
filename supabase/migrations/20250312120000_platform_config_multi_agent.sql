-- Multi-agent bundle orchestrator admin config (merged in orchestrator agent_registry)
BEGIN;

ALTER TABLE platform_config
  ADD COLUMN IF NOT EXISTS multi_agent_config JSONB NOT NULL DEFAULT '{
    "enabled": true,
    "workflow_order": [],
    "agents": []
  }'::jsonb;

COMMENT ON COLUMN platform_config.multi_agent_config IS 'Admin multi-agent: enabled, workflow_order (agent ids), agents[] overrides (display_name, skills, plan_template, user_cancellable, user_editable, enabled, workflow_order).';

COMMIT;
