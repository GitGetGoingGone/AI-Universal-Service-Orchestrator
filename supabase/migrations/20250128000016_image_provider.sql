-- Migration: Image generation provider (reuse llm_providers)
-- Date: 2025-01-28
-- Dependencies: platform_config, llm_providers

BEGIN;

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS active_image_provider_id UUID REFERENCES llm_providers(id) ON DELETE SET NULL;

-- Add 'openai' for direct OpenAI API (DALL-E, etc.)
ALTER TABLE llm_providers DROP CONSTRAINT IF EXISTS llm_providers_provider_type_check;
ALTER TABLE llm_providers ADD CONSTRAINT llm_providers_provider_type_check
  CHECK (provider_type IN ('azure', 'gemini', 'openrouter', 'custom', 'openai'));

COMMIT;
