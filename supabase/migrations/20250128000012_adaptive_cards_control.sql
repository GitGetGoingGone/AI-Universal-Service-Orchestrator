-- Migration: Response style control - conversational vs adaptive cards
-- Date: 2025-01-28
-- Dependencies: platform_config, partners

BEGIN;

-- Platform default
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS adaptive_cards_enabled BOOLEAN DEFAULT true;

-- Partner override (null = inherit from platform)
ALTER TABLE partners ADD COLUMN IF NOT EXISTS adaptive_cards_enabled BOOLEAN;

COMMIT;
