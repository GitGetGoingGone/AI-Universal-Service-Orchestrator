-- Hybrid Registry: transport_type (UCP, MCP, SHOPIFY), available_to_customize.
-- shopify_curated_partners: Shopify MCP partners with Supabase Vault token reference.

BEGIN;

-- Add columns to internal_agent_registry
ALTER TABLE internal_agent_registry
  ADD COLUMN IF NOT EXISTS transport_type TEXT NOT NULL DEFAULT 'UCP',
  ADD COLUMN IF NOT EXISTS available_to_customize BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS metadata JSONB;

CREATE INDEX IF NOT EXISTS idx_internal_agent_registry_transport_type
  ON internal_agent_registry(transport_type)
  WHERE enabled = true;

COMMENT ON COLUMN internal_agent_registry.transport_type IS 'UCP, MCP, or SHOPIFY';
COMMENT ON COLUMN internal_agent_registry.available_to_customize IS 'Partner supports customization/design chat.';
COMMENT ON COLUMN internal_agent_registry.metadata IS 'Extra data: shop_url, mcp_endpoint, capabilities when transport=SHOPIFY.';

-- shopify_curated_partners: Shopify stores with MCP endpoint and credentials
CREATE TABLE IF NOT EXISTS shopify_curated_partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
  internal_agent_registry_id UUID REFERENCES internal_agent_registry(id) ON DELETE CASCADE,
  shop_url TEXT NOT NULL,
  mcp_endpoint TEXT NOT NULL,
  supported_capabilities JSONB DEFAULT '[]',
  price_premium_percent DECIMAL(5,2) NOT NULL DEFAULT 0,
  access_token_vault_ref TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(shop_url)
);

CREATE INDEX IF NOT EXISTS idx_shopify_curated_partners_partner
  ON shopify_curated_partners(partner_id);
CREATE INDEX IF NOT EXISTS idx_shopify_curated_partners_registry
  ON shopify_curated_partners(internal_agent_registry_id);

COMMENT ON TABLE shopify_curated_partners IS 'Curated Shopify partners: MCP endpoint, capabilities, price premium. Token stored in Supabase Vault.';
COMMENT ON COLUMN shopify_curated_partners.access_token_vault_ref IS 'Reference to Supabase Vault secret for Shopify access token.';
COMMENT ON COLUMN shopify_curated_partners.price_premium_percent IS 'Admin-configurable markup per partner; 0 = no premium.';

COMMIT;
