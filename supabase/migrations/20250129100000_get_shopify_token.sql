-- RPC to retrieve decrypted Shopify access token from Vault.
-- Used by payment-service when creating/completing Shopify Draft Orders.
-- When vault extension is not available, get_shopify_token returns NULL.

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
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vault') THEN
    RETURN NULL;
  END IF;
  SELECT decrypted_secret INTO token_text
  FROM vault.decrypted_secrets
  WHERE id = vault_ref
  LIMIT 1;
  RETURN token_text;
END;
$$;

COMMENT ON FUNCTION get_shopify_token IS 'Returns decrypted Shopify access token for Draft Order API calls. Service-only. Returns NULL if vault not available.';

COMMIT;
