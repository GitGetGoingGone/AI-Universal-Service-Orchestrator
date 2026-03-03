-- Helper to store Shopify access token in Supabase Vault.
-- Requires vault extension: CREATE EXTENSION IF NOT EXISTS vault;
-- If vault is not available, skip this migration or the Admin API will accept access_token_vault_ref only.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vault;

CREATE OR REPLACE FUNCTION insert_shopify_token(secret_name TEXT, secret_value TEXT)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  secret_id UUID;
BEGIN
  SELECT vault.create_secret(secret_value, secret_name, 'Shopify partner access token') INTO secret_id;
  RETURN secret_id;
END;
$$;

COMMENT ON FUNCTION insert_shopify_token IS 'Store Shopify access token in Vault; returns secret id for storage in shopify_curated_partners.access_token_vault_ref.';

COMMIT;
