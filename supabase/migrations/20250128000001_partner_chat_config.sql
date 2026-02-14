-- Migration: Partner Chat Config (theme, branding, embed, E2E flags)
-- Date: 2025-01-28
-- Dependencies: partner_portal_production

BEGIN;

CREATE TABLE IF NOT EXISTS partner_chat_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE UNIQUE,
  -- Theme / branding
  primary_color VARCHAR(7) DEFAULT '#1976d2',
  secondary_color VARCHAR(7) DEFAULT '#424242',
  font_family VARCHAR(100) DEFAULT 'Inter, sans-serif',
  logo_url TEXT,
  welcome_message TEXT DEFAULT 'How can I help you today?',
  -- Embed
  embed_enabled BOOLEAN DEFAULT FALSE,
  embed_domains JSONB DEFAULT '[]',
  -- Feature flags (can be overridden by admin)
  e2e_add_to_bundle BOOLEAN DEFAULT TRUE,
  e2e_checkout BOOLEAN DEFAULT TRUE,
  e2e_payment BOOLEAN DEFAULT TRUE,
  -- Admin override (platform-level control)
  chat_widget_enabled BOOLEAN DEFAULT TRUE,
  admin_e2e_enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partner_chat_config_partner_id ON partner_chat_config(partner_id);

-- RLS: partners can read/update their own config
ALTER TABLE partner_chat_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY partner_chat_config_partner_select ON partner_chat_config
  FOR SELECT USING (
    partner_id IN (SELECT id FROM partners WHERE id = partner_chat_config.partner_id)
  );

CREATE POLICY partner_chat_config_partner_update ON partner_chat_config
  FOR UPDATE USING (
    partner_id IN (SELECT id FROM partners WHERE id = partner_chat_config.partner_id)
  );

CREATE POLICY partner_chat_config_partner_insert ON partner_chat_config
  FOR INSERT WITH CHECK (
    partner_id IN (SELECT id FROM partners WHERE id = partner_chat_config.partner_id)
  );

COMMIT;
