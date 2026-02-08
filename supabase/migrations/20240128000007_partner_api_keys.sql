-- Partner API keys for programmatic access (ChatGPT, Gemini, integrations)
CREATE TABLE IF NOT EXISTS partner_api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  key_hash TEXT NOT NULL,
  key_prefix TEXT NOT NULL,
  name TEXT,
  last_used_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_partner_api_keys_prefix ON partner_api_keys(key_prefix);

CREATE INDEX idx_partner_api_keys_partner_id ON partner_api_keys(partner_id);
CREATE INDEX idx_partner_api_keys_key_prefix ON partner_api_keys(key_prefix);
CREATE INDEX idx_partner_api_keys_active ON partner_api_keys(is_active) WHERE is_active = true;

COMMENT ON TABLE partner_api_keys IS 'API keys for partner programmatic access; key_hash stores HMAC-SHA256 of full key';
