-- Ensure internal_agent_registry has transport_type (and related columns).
-- Run this if you see: column internal_agent_registry.transport_type does not exist
-- (e.g. when 20250129000000_hybrid_registry_shopify was not applied).

BEGIN;

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

COMMIT;
