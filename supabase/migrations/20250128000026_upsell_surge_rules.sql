-- Migration: Upsell and Surge Rules Layer (admin-configurable)
-- Date: 2025-01-28
-- Dependencies: platform_config
-- Supports upsell_rules, surge_rules, promo_rules (promotional products at discount before checkout)

BEGIN;

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS upsell_surge_rules JSONB DEFAULT '{
  "enabled": false,
  "upsell_rules": [],
  "surge_rules": [],
  "promo_rules": []
}'::jsonb;

COMMENT ON COLUMN platform_config.upsell_surge_rules IS 'Rules for upsell (addon categories), surge pricing, and promo (discount before checkout). Admin-configurable in Platform Config.';

COMMIT;
