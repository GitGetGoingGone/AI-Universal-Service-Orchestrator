-- UCP partners: price_premium_percent and optional access_token (Vault ref) on registry.
-- available_to_customize already exists on internal_agent_registry.

BEGIN;

ALTER TABLE internal_agent_registry
  ADD COLUMN IF NOT EXISTS price_premium_percent DECIMAL(5,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS access_token_vault_ref TEXT;

COMMENT ON COLUMN internal_agent_registry.price_premium_percent IS 'Admin-configurable markup for UCP/curated partners; 0 = no premium.';
COMMENT ON COLUMN internal_agent_registry.access_token_vault_ref IS 'Reference to Supabase Vault secret for partner access token (UCP/API).';

COMMIT;
