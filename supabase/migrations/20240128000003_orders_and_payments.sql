-- Migration: Orders, Payments, Escrow (Modules 15, 16)
-- Date: 2024-01-28
-- Dependencies: intent_and_bundle

BEGIN;

-- Orders
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  bundle_id UUID REFERENCES bundles(id),
  total_amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'pending',
  payment_status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  paid_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_bundle_id ON orders(bundle_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- Order line items
CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(id),
  partner_id UUID REFERENCES partners(id),
  item_name TEXT NOT NULL,
  quantity INTEGER DEFAULT 1,
  unit_price DECIMAL(10,2) NOT NULL,
  total_price DECIMAL(10,2) NOT NULL,
  customization_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_order_items_partner_id ON order_items(partner_id);

-- Order legs
CREATE TABLE order_legs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  bundle_leg_id UUID REFERENCES bundle_legs(id),
  partner_id UUID REFERENCES partners(id),
  status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_order_legs_order_id ON order_legs(order_id);
CREATE INDEX idx_order_legs_partner_id ON order_legs(partner_id);
CREATE INDEX idx_order_legs_status ON order_legs(status);

-- Payments
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  payment_method VARCHAR(50) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'pending',
  stripe_payment_intent_id TEXT,
  transaction_id TEXT,
  failure_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  authorized_at TIMESTAMPTZ,
  captured_at TIMESTAMPTZ,
  failed_at TIMESTAMPTZ
);

CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_stripe_intent ON payments(stripe_payment_intent_id);

-- Payment splits
CREATE TABLE payment_splits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_id UUID REFERENCES payments(id) ON DELETE CASCADE,
  recipient_type VARCHAR(20) NOT NULL,
  recipient_id UUID,
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  split_type VARCHAR(20),
  status VARCHAR(20) DEFAULT 'pending',
  stripe_transfer_id TEXT,
  transferred_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payment_splits_payment_id ON payment_splits(payment_id);
CREATE INDEX idx_payment_splits_recipient ON payment_splits(recipient_type, recipient_id);

-- Escrow accounts
CREATE TABLE escrow_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  total_amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'held',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  released_at TIMESTAMPTZ,
  refunded_at TIMESTAMPTZ
);

CREATE INDEX idx_escrow_accounts_order_id ON escrow_accounts(order_id);
CREATE INDEX idx_escrow_accounts_status ON escrow_accounts(status);

-- Escrow transactions
CREATE TABLE escrow_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  escrow_account_id UUID REFERENCES escrow_accounts(id) ON DELETE CASCADE,
  transaction_type VARCHAR(20) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  recipient_id UUID,
  recipient_type VARCHAR(20),
  status VARCHAR(20) DEFAULT 'pending',
  transaction_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_escrow_transactions_account_id ON escrow_transactions(escrow_account_id);

-- Escrow releases
CREATE TABLE escrow_releases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  escrow_account_id UUID REFERENCES escrow_accounts(id) ON DELETE CASCADE,
  order_leg_id UUID REFERENCES order_legs(id),
  release_trigger VARCHAR(50) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  recipient_id UUID NOT NULL,
  recipient_type VARCHAR(20) NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  released_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_escrow_releases_account_id ON escrow_releases(escrow_account_id);

COMMIT;
