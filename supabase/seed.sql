-- Seed data for local development
-- Run after migrations. Safe to run multiple times (uses ON CONFLICT where applicable).

-- Test user (Clerk sync would populate this in production)
INSERT INTO users (id, email, legal_name, display_name, created_at, updated_at)
VALUES (
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'dev@example.com',
  'Dev User',
  'Dev',
  NOW(),
  NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Capability tags (Module 7)
INSERT INTO capability_tags (tag_name, tag_category, description) VALUES
  ('flowers', 'product', 'Fresh flowers and bouquets'),
  ('chocolates', 'product', 'Custom and premium chocolates'),
  ('limo', 'service', 'Luxury limousine transport'),
  ('dinner_reservation', 'service', 'Restaurant reservations'),
  ('customization', 'product', 'Custom engraving, packaging')
ON CONFLICT (tag_name) DO NOTHING;

-- Sample partner
INSERT INTO partners (
  id,
  user_id,
  business_name,
  business_type,
  contact_email,
  verification_status,
  trust_score,
  is_active,
  created_at,
  updated_at
) VALUES (
  'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'Flower Shop Demo',
  'retail',
  'partner@example.com',
  'verified',
  85,
  true,
  NOW(),
  NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Sample product (description includes "flowers" for search matching)
INSERT INTO products (
  id,
  partner_id,
  name,
  description,
  price,
  currency,
  capabilities,
  created_at,
  updated_at
) VALUES (
  'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33',
  'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
  'Red Roses Bouquet',
  'A dozen fresh red roses - flowers for any occasion',
  49.99,
  'USD',
  '["flowers"]'::jsonb,
  NOW(),
  NOW()
)
ON CONFLICT (id) DO UPDATE SET
  description = EXCLUDED.description,
  updated_at = NOW();
