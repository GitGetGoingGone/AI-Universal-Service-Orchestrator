-- Migration: External API Providers (runtime-configurable events, weather, web search)
-- Date: 2025-01-28
-- Dependencies: platform_config

BEGIN;

CREATE TABLE IF NOT EXISTS external_api_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  api_type TEXT NOT NULL,
  base_url TEXT,
  api_key_encrypted TEXT,
  extra_config JSONB DEFAULT '{}',
  enabled BOOLEAN DEFAULT true,
  display_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_external_api_providers_api_type ON external_api_providers(api_type);
CREATE INDEX IF NOT EXISTS idx_external_api_providers_display_order ON external_api_providers(display_order);

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS active_external_api_ids JSONB DEFAULT '{}';

COMMENT ON TABLE external_api_providers IS 'Runtime-configurable external APIs (events, weather, web_search). Keys stored encrypted.';
COMMENT ON COLUMN platform_config.active_external_api_ids IS 'Maps api_type to provider id, e.g. {"web_search":"uuid","weather":"uuid","events":"uuid"}';

ALTER TABLE external_api_providers ENABLE ROW LEVEL SECURITY;

COMMIT;
