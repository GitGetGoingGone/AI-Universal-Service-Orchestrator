-- Migration: Chat typing and font size config (partner_chat_config)
-- Date: 2025-01-28
-- Dependencies: partner_chat_config

BEGIN;

ALTER TABLE partner_chat_config ADD COLUMN IF NOT EXISTS chat_typing_enabled BOOLEAN DEFAULT true;
COMMENT ON COLUMN partner_chat_config.chat_typing_enabled IS 'When true, assistant text uses typewriter effect. When false, text appears instantly.';

ALTER TABLE partner_chat_config ADD COLUMN IF NOT EXISTS chat_typing_speed_ms INTEGER DEFAULT 30;
COMMENT ON COLUMN partner_chat_config.chat_typing_speed_ms IS 'Milliseconds per character for typewriter effect. Lower = faster.';

ALTER TABLE partner_chat_config ADD COLUMN IF NOT EXISTS font_size_px INTEGER DEFAULT 14;
COMMENT ON COLUMN partner_chat_config.font_size_px IS 'Base font size in pixels for chat content.';

COMMIT;
