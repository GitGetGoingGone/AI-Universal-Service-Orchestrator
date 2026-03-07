-- Migration: retry_phrases on platform_config (admin config for re-engagement / probing phrases)
-- experience_flow_rules is stored inside composite_discovery_config JSONB; no new column needed.

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS retry_phrases JSONB DEFAULT '[]'::jsonb;
COMMENT ON COLUMN platform_config.retry_phrases IS 'Optional phrases for re-engagement or probing (e.g. "Want to try again?"). Admin-configurable in Platform Config.';
