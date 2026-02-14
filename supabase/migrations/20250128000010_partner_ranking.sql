-- Migration: Partner Ranking and Sponsorship (Part 4)
-- Date: 2025-01-28
-- Dependencies: platform_config, products, partners

BEGIN;

-- platform_config: ranking and sponsorship settings
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS ranking_enabled BOOLEAN DEFAULT true;
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS ranking_policy JSONB DEFAULT '{"strategy":"weighted","weights":{"price":0.3,"rating":0.3,"commission":0.2,"trust":0.2},"price_direction":"asc"}'::jsonb;
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS ranking_edge_cases JSONB DEFAULT '{"missing_rating":0.5,"missing_commission":0,"missing_trust":0.5,"tie_breaker":"created_at"}'::jsonb;
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS sponsorship_pricing JSONB DEFAULT '{"product_price_per_day_cents":1000,"max_sponsored_per_query":3,"sponsorship_enabled":true}'::jsonb;

-- product_sponsorships: paid product boosts
CREATE TABLE IF NOT EXISTS product_sponsorships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  start_at TIMESTAMPTZ NOT NULL,
  end_at TIMESTAMPTZ NOT NULL,
  amount_cents INTEGER NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'active',
  stripe_payment_intent_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_sponsorships_product ON product_sponsorships(product_id);
CREATE INDEX IF NOT EXISTS idx_product_sponsorships_partner ON product_sponsorships(partner_id);
CREATE INDEX IF NOT EXISTS idx_product_sponsorships_dates ON product_sponsorships(start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_product_sponsorships_status ON product_sponsorships(status) WHERE status = 'active';

COMMIT;
