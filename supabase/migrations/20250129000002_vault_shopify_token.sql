-- Helper to store Shopify access token in Supabase Vault (when available).
-- If the vault extension is not installed (e.g. local PostgreSQL), the extension
-- is skipped and insert_shopify_token is a stub that raises; access_token remains optional.

BEGIN;

-- Try to enable vault; ignore error if extension is not available
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS vault;
EXCEPTION
  WHEN OTHERS THEN
    NULL; -- vault not available (e.g. local pg), continue
END $$;

-- Create insert_shopify_token: real implementation when vault exists, stub otherwise
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vault') THEN
    EXECUTE $exec$
      CREATE OR REPLACE FUNCTION insert_shopify_token(secret_name TEXT, secret_value TEXT)
      RETURNS UUID
      LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
      AS $func$
      DECLARE secret_id UUID;
      BEGIN
        SELECT vault.create_secret(secret_value, secret_name, 'Shopify partner access token') INTO secret_id;
        RETURN secret_id;
      END;
      $func$;
    $exec$;
    COMMENT ON FUNCTION insert_shopify_token(TEXT, TEXT) IS 'Store Shopify access token in Vault; returns secret id for storage in shopify_curated_partners.access_token_vault_ref.';
  ELSE
    EXECUTE $exec$
      CREATE OR REPLACE FUNCTION insert_shopify_token(secret_name TEXT, secret_value TEXT)
      RETURNS UUID
      LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
      AS $func$
      BEGIN
        RAISE EXCEPTION 'Vault extension not available; cannot store access_token. Use Supabase or install vault.';
      END;
      $func$;
    $exec$;
  END IF;
END $$;

COMMIT;
