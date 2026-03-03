-- RPC to retrieve decrypted Shopify access token from Vault.
-- Used by payment-service when creating/completing Shopify Draft Orders.
-- Requires vault extension and that the secret was stored via insert_shopify_token.

BEGIN;

CREATE OR REPLACE FUNCTION get_shopify_token(vault_ref UUID)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  token_text TEXT;
BEGIN
  SELECT decrypted_secret INTO token_text
  FROM vault.decrypted_secrets
  WHERE id = vault_ref
  LIMIT 1;
  RETURN token_text;
END;
$$;

COMMENT ON FUNCTION get_shopify_token IS 'Returns decrypted Shopify access token for Draft Order API calls. Service-only.';

COMMIT;
