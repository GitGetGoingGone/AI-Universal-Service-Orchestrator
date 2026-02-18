-- Migration: Thinking UI Admin Config (font, color, animation, message templates)
-- Date: 2025-01-28
-- Dependencies: platform_config

BEGIN;

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS thinking_ui JSONB DEFAULT '{
  "font_size_px": 14,
  "color": "#94a3b8",
  "animation_type": "dots",
  "animation_speed_ms": 1000
}'::jsonb;

COMMENT ON COLUMN platform_config.thinking_ui IS 'Display settings for thinking progress: font_size_px (12-24), color (hex), animation_type (pulse|fade|dots|none), animation_speed_ms. Admin-configurable in Platform Config.';

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS thinking_messages JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN platform_config.thinking_messages IS 'Optional overrides for thinking step message templates. Keys match step names; {location}, {query}, {experience_name} interpolated. Admin-configurable in Platform Config.';

COMMIT;
