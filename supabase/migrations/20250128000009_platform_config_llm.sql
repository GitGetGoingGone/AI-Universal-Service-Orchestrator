-- Migration: Add LLM settings to platform_config (Admin LLM Config)
-- Date: 2025-01-28
-- Dependencies: platform_config

BEGIN;

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS llm_provider TEXT DEFAULT 'openai';
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS llm_model TEXT DEFAULT 'gpt-4o';
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS llm_temperature DECIMAL(3,2) DEFAULT 0.10;

COMMIT;
