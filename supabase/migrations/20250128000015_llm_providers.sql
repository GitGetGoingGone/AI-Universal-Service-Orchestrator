-- Migration: LLM Providers (runtime-configurable LLMs)
-- Date: 2025-01-28
-- Dependencies: platform_config

BEGIN;

CREATE TABLE IF NOT EXISTS llm_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  provider_type TEXT NOT NULL CHECK (provider_type IN ('azure', 'gemini', 'openrouter', 'custom')),
  endpoint TEXT,
  api_key_encrypted TEXT,
  model TEXT NOT NULL,
  display_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_providers_provider_type ON llm_providers(provider_type);
CREATE INDEX IF NOT EXISTS idx_llm_providers_display_order ON llm_providers(display_order);

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS active_llm_provider_id UUID REFERENCES llm_providers(id) ON DELETE SET NULL;

ALTER TABLE llm_providers ENABLE ROW LEVEL SECURITY;

-- No permissive policies: anon/authenticated get no access. Portal and orchestrator use service_role which bypasses RLS.
-- Platform admin check is enforced at the API route level (isPlatformAdmin).

COMMIT;
