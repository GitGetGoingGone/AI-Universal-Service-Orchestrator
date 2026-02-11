-- Migration: Reverse Logistics (Module 17) - Returns, refunds, restocking
-- Dependencies: orders_and_payments, full_implementation_support (product_inventory)

BEGIN;

-- Return requests (RMA)
CREATE TABLE return_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  order_leg_id UUID REFERENCES order_legs(id) ON DELETE SET NULL,
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  requester_id UUID REFERENCES users(id) ON DELETE SET NULL,
  reason VARCHAR(50) NOT NULL,
  reason_detail TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  photo_url TEXT,
  items JSONB,
  refund_amount_cents INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  approved_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  metadata JSONB
);

CREATE INDEX idx_return_requests_order_id ON return_requests(order_id);
CREATE INDEX idx_return_requests_partner_id ON return_requests(partner_id);
CREATE INDEX idx_return_requests_status ON return_requests(status);

-- Refunds (links to payment/escrow)
CREATE TABLE refunds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  return_request_id UUID REFERENCES return_requests(id) ON DELETE CASCADE,
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  amount_cents INTEGER NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  stripe_refund_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_refunds_return_request_id ON refunds(return_request_id);
CREATE INDEX idx_refunds_order_id ON refunds(order_id);

-- Restock events (inventory updates from returns)
CREATE TABLE restock_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  return_request_id UUID REFERENCES return_requests(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  quantity INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_restock_events_return_request_id ON restock_events(return_request_id);
CREATE INDEX idx_restock_events_product_id ON restock_events(product_id);

COMMENT ON TABLE return_requests IS 'Module 17: Return requests (RMA) for reverse logistics';
COMMENT ON TABLE refunds IS 'Module 17: Refunds linked to return requests';
COMMENT ON TABLE restock_events IS 'Module 17: Inventory restock from returns';

COMMIT;
