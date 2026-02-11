-- Seed for Phase 2 real-life test scenario (Task Queue, HubNegotiator, Hybrid Response)
-- Run after main migrations and seed.sql. Creates: second partner, hub, products, bundle, order, order_legs.
-- See docs/REAL_LIFE_TEST_SCENARIO.md for the test flow.

-- Second vendor (Chocolate Co.)
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES (
  'b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a23',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'Chocolate Co. Demo',
  'retail',
  'chocolate@example.com',
  'verified',
  88,
  true,
  NOW(),
  NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Hub partner (assembly/delivery)
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES (
  'b3eebc99-9c0b-4ef8-bb6d-6bb9bd380a24',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'FastHub Assembly',
  'fulfillment',
  'hub@example.com',
  'verified',
  90,
  true,
  NOW(),
  NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Chocolate product
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, created_at, updated_at)
VALUES (
  'c3eebc99-9c0b-4ef8-bb6d-6bb9bd380a34',
  'b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a23',
  'Premium Chocolates',
  'Assorted gourmet chocolates',
  29.99,
  'USD',
  '["chocolates"]'::jsonb,
  NOW(),
  NOW()
)
ON CONFLICT (id) DO UPDATE SET description = EXCLUDED.description, updated_at = NOW();

-- Bundle (flowers + chocolates)
INSERT INTO bundles (id, user_id, bundle_name, total_price, currency, status, created_at)
VALUES (
  'd1eebc99-9c0b-4ef8-bb6d-6bb9bd380a40',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'Gift Bundle',
  79.98,
  'USD',
  'draft',
  NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Bundle legs (order: flowers first, chocolates second)
INSERT INTO bundle_legs (id, bundle_id, product_id, partner_id, leg_sequence, leg_type, price, created_at)
VALUES
  ('d2eebc99-9c0b-4ef8-bb6d-6bb9bd380a41', 'd1eebc99-9c0b-4ef8-bb6d-6bb9bd380a40', 'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 1, 'product', 49.99, NOW()),
  ('d3eebc99-9c0b-4ef8-bb6d-6bb9bd380a42', 'd1eebc99-9c0b-4ef8-bb6d-6bb9bd380a40', 'c3eebc99-9c0b-4ef8-bb6d-6bb9bd380a34', 'b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a23', 2, 'product', 29.99, NOW())
ON CONFLICT (id) DO NOTHING;

-- Order
INSERT INTO orders (id, user_id, bundle_id, total_amount, currency, status, payment_status, created_at)
VALUES (
  'e1eebc99-9c0b-4ef8-bb6d-6bb9bd380a50',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'd1eebc99-9c0b-4ef8-bb6d-6bb9bd380a40',
  79.98,
  'USD',
  'pending',
  'pending',
  NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Order legs (one per vendor)
INSERT INTO order_legs (id, order_id, bundle_leg_id, partner_id, status, created_at)
VALUES
  ('e2eebc99-9c0b-4ef8-bb6d-6bb9bd380a51', 'e1eebc99-9c0b-4ef8-bb6d-6bb9bd380a50', 'd2eebc99-9c0b-4ef8-bb6d-6bb9bd380a41', 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'pending', NOW()),
  ('e3eebc99-9c0b-4ef8-bb6d-6bb9bd380a52', 'e1eebc99-9c0b-4ef8-bb6d-6bb9bd380a50', 'd3eebc99-9c0b-4ef8-bb6d-6bb9bd380a42', 'b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a23', 'pending', NOW())
ON CONFLICT (id) DO NOTHING;

-- IDs for docs/REAL_LIFE_TEST_SCENARIO.md:
-- ORDER_UUID:        e1eebc99-9c0b-4ef8-bb6d-6bb9bd380a50
-- BUNDLE_UUID:      d1eebc99-9c0b-4ef8-bb6d-6bb9bd380a40
-- FLOWER_PARTNER:   b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22
-- CHOCOLATE_PARTNER: b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a23
-- HUB_PARTNER:      b3eebc99-9c0b-4ef8-bb6d-6bb9bd380a24
-- USER_UUID:        a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
