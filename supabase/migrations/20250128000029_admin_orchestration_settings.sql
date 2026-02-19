-- Migration: Admin Orchestration Settings
-- Phase 1: Protocol-Aware, Admin-Controlled Orchestrator
-- Date: 2025-01-28
-- Dependencies: platform_config

BEGIN;

CREATE TABLE IF NOT EXISTS admin_orchestration_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  global_tone TEXT DEFAULT 'warm, elegant, memorable',
  model_temperature DECIMAL(3,2) DEFAULT 0.7 CHECK (model_temperature >= 0 AND model_temperature <= 2.0),
  autonomy_level TEXT DEFAULT 'balanced' CHECK (autonomy_level IN ('conservative', 'balanced', 'aggressive')),
  discovery_timeout_ms INT DEFAULT 5000 CHECK (discovery_timeout_ms >= 500 AND discovery_timeout_ms <= 60000),
  ucp_prioritized BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default row if empty
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM admin_orchestration_settings LIMIT 1) THEN
    INSERT INTO admin_orchestration_settings (global_tone, model_temperature, autonomy_level, discovery_timeout_ms, ucp_prioritized)
    VALUES ('warm, elegant, memorable', 0.7, 'balanced', 5000, false);
  END IF;
END $$;

COMMENT ON TABLE admin_orchestration_settings IS 'Admin-controlled orchestration: tone, temperature, autonomy, discovery timeout';
COMMENT ON COLUMN admin_orchestration_settings.global_tone IS 'Injected into engagement prompts (e.g. warm, elegant, memorable)';
COMMENT ON COLUMN admin_orchestration_settings.model_temperature IS 'LLM temperature for creative responses (0-2)';
COMMENT ON COLUMN admin_orchestration_settings.autonomy_level IS 'conservative=more probing, balanced, aggressive=assume defaults';
COMMENT ON COLUMN admin_orchestration_settings.discovery_timeout_ms IS 'Timeout for discovery aggregator fan-out (ms)';

COMMIT;
