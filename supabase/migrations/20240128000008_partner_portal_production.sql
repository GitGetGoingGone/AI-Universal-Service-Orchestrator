-- Migration: Partner Portal Production (schedule, team, admins, earnings, analytics, etc.)
-- Date: 2024-01-28
-- Dependencies: core_and_scout, orders_and_payments, timechain_recovery_support

BEGIN;

-- 1.1 Partner members and platform admins
CREATE TABLE IF NOT EXISTS partner_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  email TEXT NOT NULL,
  display_name TEXT,
  role VARCHAR(20) NOT NULL DEFAULT 'member',
  invited_at TIMESTAMPTZ DEFAULT NOW(),
  joined_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(partner_id, email)
);

CREATE INDEX IF NOT EXISTS idx_partner_members_partner_id ON partner_members(partner_id);
CREATE INDEX IF NOT EXISTS idx_partner_members_user_id ON partner_members(user_id);

CREATE TABLE IF NOT EXISTS platform_admins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scope VARCHAR(20) DEFAULT 'all',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id)
);

-- 1.2 Business hours
CREATE TABLE IF NOT EXISTS partner_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  day_of_week SMALLINT NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  timezone VARCHAR(50) DEFAULT 'UTC',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partner_schedules_partner_id ON partner_schedules(partner_id);

-- 1.3 Product price range
ALTER TABLE products ADD COLUMN IF NOT EXISTS price_min DECIMAL(10,2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS price_max DECIMAL(10,2);

-- 1.4 Product availability (bookable slots)
CREATE TABLE IF NOT EXISTS product_availability (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  slot_type VARCHAR(20) NOT NULL,
  start_at TIMESTAMPTZ NOT NULL,
  end_at TIMESTAMPTZ NOT NULL,
  capacity INTEGER DEFAULT 1,
  booking_mode VARCHAR(30) NOT NULL DEFAULT 'auto_book',
  timezone VARCHAR(50) DEFAULT 'UTC',
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_availability_product_id ON product_availability(product_id);

-- 1.4a Availability integrations
CREATE TABLE IF NOT EXISTS availability_integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  integration_type VARCHAR(30) NOT NULL,
  provider VARCHAR(50),
  config JSONB NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  last_sync_at TIMESTAMPTZ,
  last_sync_status VARCHAR(20),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_availability_integrations_partner_id ON availability_integrations(partner_id);

-- 1.5 Product-team assignments
CREATE TABLE IF NOT EXISTS product_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  partner_member_id UUID NOT NULL REFERENCES partner_members(id) ON DELETE CASCADE,
  role VARCHAR(20) DEFAULT 'handler',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, partner_member_id)
);

CREATE INDEX IF NOT EXISTS idx_product_assignments_product_id ON product_assignments(product_id);

-- 1.6 Earnings and payouts
CREATE TABLE IF NOT EXISTS payouts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  stripe_payout_id TEXT,
  amount_cents INTEGER NOT NULL,
  fee_cents INTEGER DEFAULT 0,
  status VARCHAR(20) DEFAULT 'pending',
  settled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payouts_partner_id ON payouts(partner_id);

CREATE TABLE IF NOT EXISTS commission_breaks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id),
  partner_id UUID NOT NULL REFERENCES partners(id),
  gross_cents INTEGER NOT NULL,
  commission_cents INTEGER NOT NULL,
  net_cents INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_commission_breaks_partner_id ON commission_breaks(partner_id);

-- 1.7 Menu / catalog enhancements
ALTER TABLE products ADD COLUMN IF NOT EXISTS is_available BOOLEAN DEFAULT TRUE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url TEXT;

CREATE TABLE IF NOT EXISTS product_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sort_order SMALLINT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_categories_partner_id ON product_categories(partner_id);

ALTER TABLE products ADD COLUMN IF NOT EXISTS category_id UUID REFERENCES product_categories(id);

CREATE TABLE IF NOT EXISTS product_modifiers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  price_delta DECIMAL(10,2) DEFAULT 0,
  is_required BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_modifiers_product_id ON product_modifiers(product_id);

-- 1.8 Inventory
CREATE TABLE IF NOT EXISTS product_inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  quantity INTEGER NOT NULL DEFAULT 0,
  low_stock_threshold INTEGER DEFAULT 5,
  auto_unlist_when_zero BOOLEAN DEFAULT TRUE,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id)
);

CREATE INDEX IF NOT EXISTS idx_product_inventory_product_id ON product_inventory(product_id);

-- 1.9 Promotions
CREATE TABLE IF NOT EXISTS partner_promotions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  promo_type VARCHAR(20) NOT NULL,
  value DECIMAL(10,2),
  product_ids UUID[],
  start_at TIMESTAMPTZ NOT NULL,
  end_at TIMESTAMPTZ NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partner_promotions_partner_id ON partner_promotions(partner_id);

-- 1.10 Operations
ALTER TABLE partners ADD COLUMN IF NOT EXISTS is_accepting_orders BOOLEAN DEFAULT TRUE;
ALTER TABLE partners ADD COLUMN IF NOT EXISTS capacity_limit INTEGER;

CREATE TABLE IF NOT EXISTS partner_venues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  address JSONB,
  timezone VARCHAR(50) DEFAULT 'UTC',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partner_venues_partner_id ON partner_venues(partner_id);

CREATE TABLE IF NOT EXISTS partner_service_areas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  venue_id UUID REFERENCES partner_venues(id),
  geometry GEOMETRY(Polygon, 4326),
  radius_km DECIMAL(10,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partner_service_areas_partner_id ON partner_service_areas(partner_id);

-- 1.11 Ratings and reviews
CREATE TABLE IF NOT EXISTS partner_ratings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  avg_rating DECIMAL(3,2) NOT NULL,
  total_reviews INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(partner_id)
);

CREATE TABLE IF NOT EXISTS order_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  rating SMALLINT NOT NULL,
  comment TEXT,
  partner_response TEXT,
  responded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_reviews_partner_id ON order_reviews(partner_id);

-- 1.12 Notifications
CREATE TABLE IF NOT EXISTS partner_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  type VARCHAR(30) NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  payload JSONB,
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partner_notifications_partner_id ON partner_notifications(partner_id);

CREATE TABLE IF NOT EXISTS notification_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  type VARCHAR(30) NOT NULL,
  email_enabled BOOLEAN DEFAULT TRUE,
  push_enabled BOOLEAN DEFAULT FALSE,
  in_app_enabled BOOLEAN DEFAULT TRUE,
  UNIQUE(partner_id, type)
);

CREATE INDEX IF NOT EXISTS idx_notification_preferences_partner_id ON notification_preferences(partner_id);

-- 1.13 Order status (extend order_legs)
ALTER TABLE order_legs ADD COLUMN IF NOT EXISTS preparation_mins INTEGER;
ALTER TABLE order_legs ADD COLUMN IF NOT EXISTS reject_reason TEXT;

COMMIT;
