-- Migration: Pillar 1 (product_inventory, affiliate) + Pillar 4 (SLA, kill_switch)
-- Dependencies: platform_config, core_and_scout

BEGIN;

-- Pillar 1: Product inventory (sync from partners)
-- Table may already exist from partner_portal_production; add missing columns
CREATE TABLE IF NOT EXISTS product_inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  quantity INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id)
);

ALTER TABLE product_inventory ADD COLUMN IF NOT EXISTS partner_id UUID REFERENCES partners(id) ON DELETE CASCADE;
ALTER TABLE product_inventory ADD COLUMN IF NOT EXISTS reserved_quantity INTEGER DEFAULT 0;
ALTER TABLE product_inventory ADD COLUMN IF NOT EXISTS sync_method VARCHAR(50) DEFAULT 'webhook';
ALTER TABLE product_inventory ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ;
ALTER TABLE product_inventory ADD COLUMN IF NOT EXISTS source_system TEXT;

CREATE INDEX IF NOT EXISTS idx_product_inventory_product ON product_inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_product_inventory_partner ON product_inventory(partner_id);

-- Pillar 1: Affiliate link tracking
CREATE TABLE IF NOT EXISTS affiliate_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  partner_id UUID REFERENCES partners(id) ON DELETE SET NULL,
  affiliate_network VARCHAR(100),
  affiliate_url TEXT NOT NULL,
  commission_rate DECIMAL(5,2),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_affiliate_links_product ON affiliate_links(product_id);
CREATE INDEX idx_affiliate_links_partner ON affiliate_links(partner_id);

-- Pillar 4: SLA and kill switch in platform_config
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS sla_response_time_ms INTEGER DEFAULT 3000;
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS sla_availability_pct DECIMAL(5,2) DEFAULT 99.50;
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS requires_human_approval_over_cents INTEGER DEFAULT 20000;
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS delivery_buffer_minutes INTEGER DEFAULT 15;
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS kill_switch_active BOOLEAN DEFAULT FALSE;
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS kill_switch_reason TEXT;
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS kill_switch_activated_at TIMESTAMPTZ;

-- Pillar 4: Kill switch event log
CREATE TABLE IF NOT EXISTS kill_switch_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  activated BOOLEAN NOT NULL,
  reason TEXT,
  activated_by UUID REFERENCES users(id),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kill_switch_events_created ON kill_switch_events(created_at DESC);

COMMENT ON TABLE product_inventory IS 'Pillar 1: Partner inventory sync (webhook or poll)';
COMMENT ON TABLE affiliate_links IS 'Pillar 1: Affiliate link tracking for Scout Engine';
COMMENT ON TABLE kill_switch_events IS 'Pillar 4: Kill switch activation/deactivation log';

COMMIT;
