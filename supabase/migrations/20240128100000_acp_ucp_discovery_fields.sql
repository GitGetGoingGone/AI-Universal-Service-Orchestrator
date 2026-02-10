-- ACP/UCP discovery: partner seller attribution and product ACP fields for ChatGPT/Gemini discovery.
-- Reference: docs/COMMERCE_FEED_SCHEMA_REQUIREMENTS.md, docs/AI_PLATFORM_PRODUCT_DISCOVERY.md

BEGIN;

-- Partners: seller attribution (ACP feed and UCP catalog) and 15-min ACP push throttle
ALTER TABLE partners ADD COLUMN IF NOT EXISTS seller_name TEXT;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS seller_url TEXT;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS return_policy_url TEXT;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS privacy_policy_url TEXT;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS terms_url TEXT;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS store_country VARCHAR(2);
ALTER TABLE partners ADD COLUMN IF NOT EXISTS target_countries JSONB;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS last_acp_push_at TIMESTAMPTZ;

COMMENT ON COLUMN partners.seller_name IS 'Display name for ACP/UCP (e.g. business_name); max 70 for ACP';
COMMENT ON COLUMN partners.seller_url IS 'Partner site or profile URL for ACP/UCP';
COMMENT ON COLUMN partners.return_policy_url IS 'Return policy URL for ACP feed';
COMMENT ON COLUMN partners.privacy_policy_url IS 'Privacy policy URL when is_eligible_checkout';
COMMENT ON COLUMN partners.terms_url IS 'Terms of service URL when is_eligible_checkout';
COMMENT ON COLUMN partners.store_country IS 'ISO 3166-1 alpha-2';
COMMENT ON COLUMN partners.target_countries IS 'ISO 3166-1 alpha-2 list for ACP';
COMMENT ON COLUMN partners.last_acp_push_at IS 'Last ACP catalog push time; 15-min throttle per partner';

-- Products: ACP fields for feed export (url, brand, eligibility, availability)
ALTER TABLE products ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS brand VARCHAR(70);
ALTER TABLE products ADD COLUMN IF NOT EXISTS is_eligible_search BOOLEAN DEFAULT TRUE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS is_eligible_checkout BOOLEAN DEFAULT FALSE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS target_countries JSONB;
ALTER TABLE products ADD COLUMN IF NOT EXISTS availability VARCHAR(20) DEFAULT 'in_stock';

COMMENT ON COLUMN products.url IS 'Product detail page URL for ACP';
COMMENT ON COLUMN products.brand IS 'Brand name for ACP; max 70';
COMMENT ON COLUMN products.is_eligible_search IS 'Product can appear in ChatGPT search';
COMMENT ON COLUMN products.is_eligible_checkout IS 'Direct purchase in ChatGPT';
COMMENT ON COLUMN products.target_countries IS 'ISO 3166-1 alpha-2 list for ACP';
COMMENT ON COLUMN products.availability IS 'in_stock, out_of_stock, pre_order, backorder, unknown';

COMMIT;
