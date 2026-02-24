-- Seed data for local development
-- Compliant with current schema: users, capability_tags, partners, products (experience_tags, capabilities),
-- partner_kb_articles (KB-based discovery), bundles, bundle_legs, orders, order_legs.
-- Optional columns (description_kb, sold_count, etc.) are left default/NULL.
-- 7 test partners with synthetic products (flowers, chocolates, limos, movies, events, restaurant, baby)
-- Tots Trunk: baby/newborn + pre-bundled products; plus KB entries for custom bundle and personalized letter (not products).
-- Run after migrations. Safe to run multiple times (ON CONFLICT).

BEGIN;

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

-- Capability tags (Module 7 + seed categories)
INSERT INTO capability_tags (tag_name, tag_category, description) VALUES
  ('flowers', 'product', 'Fresh flowers and bouquets'),
  ('chocolates', 'product', 'Custom and premium chocolates'),
  ('limo', 'service', 'Luxury limousine transport'),
  ('dinner_reservation', 'service', 'Restaurant reservations'),
  ('restaurant', 'service', 'Restaurant dining and reservations'),
  ('customization', 'product', 'Custom engraving, packaging'),
  ('movies', 'service', 'Movie tickets and cinema experiences'),
  ('events', 'service', 'Concerts, shows, and events'),
  ('baby', 'product', 'Baby and nursery products'),
  ('newborn', 'product', 'Newborn essentials'),
  ('bundle', 'product', 'Pre-bundled product set'),
  ('gifts', 'product', 'Gift-oriented products')
ON CONFLICT (tag_name) DO NOTHING;

-- Partner 1: Bloom & Petals (flowers, chocolates, limos, movies, events, restaurant)
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES ('a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Bloom & Petals', 'retail', 'bloom@test.example.com', 'approved', 90, true, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Partner 2: Sweet Treats Co
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES ('a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Sweet Treats Co', 'retail', 'sweet@test.example.com', 'approved', 88, true, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Partner 3: Luxe Rides
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES ('a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Luxe Rides', 'service', 'luxe@test.example.com', 'approved', 92, true, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Partner 4: Cinema Plus
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES ('a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Cinema Plus', 'service', 'cinema@test.example.com', 'approved', 85, true, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Partner 5: Event Central
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES ('a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Event Central', 'service', 'events@test.example.com', 'approved', 87, true, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Partner 6: Gourmet Bites
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES ('a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Gourmet Bites', 'retail', 'gourmet@test.example.com', 'approved', 91, true, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Partner 7: Tots Trunk (baby items + pre-bundled products)
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES ('a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'Tots Trunk', 'retail', 'tots@test.example.com', 'approved', 89, true, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Products: ~15 per partner with experience_tags
-- Partner 1: Bloom & Petals
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, experience_tags, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000001-0001-4001-8001-000000000001', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Classic Red Roses', 'A dozen fresh red roses - perfect for anniversaries and romance', 59.99, 'USD', '["flowers"]'::jsonb, '["celebration", "romantic", "gift", "luxury"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000002', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Mixed Spring Bouquet', 'Colorful mix of tulips, daisies, and lilies - flowers for any occasion', 45.00, 'USD', '["flowers"]'::jsonb, '["celebration", "gift", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000003', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Premium Orchid Arrangement', 'Elegant orchid plant - luxury flowers for gifting', 89.99, 'USD', '["flowers"]'::jsonb, '["luxury", "celebration", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000004', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Belgian Chocolate Box', 'Assorted premium Belgian chocolates - 24 pieces', 34.99, 'USD', '["chocolates"]'::jsonb, '["gift", "celebration", "luxury", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000005', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Truffle Sampler', 'Gourmet dark and milk chocolate truffles - chocolates for date night', 42.00, 'USD', '["chocolates"]'::jsonb, '["gift", "luxury", "romantic", "night out"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000006', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Limo 4-Hour Package', 'Luxury limo for 4 hours - perfect for date night or events', 299.00, 'USD', '["limo"]'::jsonb, '["luxury", "night out", "travel", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000007', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Stretch Limo Airport Transfer', 'Premium limo airport pickup or drop-off', 149.00, 'USD', '["limo"]'::jsonb, '["luxury", "travel", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000008', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Movie Night Duo Pass', 'Two movie tickets with popcorn and drinks', 35.00, 'USD', '["movies"]'::jsonb, '["night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000009', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'IMAX Premium Experience', 'IMAX movie tickets for two - best movies experience', 48.00, 'USD', '["movies"]'::jsonb, '["night out", "romantic", "luxury"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000a', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Concert VIP Package', 'VIP access to live concert - events and entertainment', 199.00, 'USD', '["events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000b', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Comedy Show Tickets', 'Two tickets to stand-up comedy show - fun events', 55.00, 'USD', '["events"]'::jsonb, '["night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000c', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Romantic Dinner for Two', '3-course dinner at upscale restaurant - reservation included', 120.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000d', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Brunch Experience', 'Sunday brunch for two at top-rated restaurant', 75.00, 'USD', '["restaurant"]'::jsonb, '["celebration", "romantic", "family"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000e', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Chef''s Tasting Menu', '5-course tasting menu - fine dining restaurant experience', 185.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000f', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Sunflower Bouquet', 'Bright sunflowers - cheerful flowers for any day', 39.99, 'USD', '["flowers"]'::jsonb, '["celebration", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, capabilities = EXCLUDED.capabilities, experience_tags = EXCLUDED.experience_tags, updated_at = NOW();

-- Partner 2: Sweet Treats Co
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, experience_tags, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000002-0001-4001-8001-000000000001', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Birthday Flower Bouquet', 'Colorful birthday flowers with balloon', 52.00, 'USD', '["flowers"]'::jsonb, '["celebration", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000002', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Dark Chocolate Collection', 'Artisan dark chocolates - 16 pieces premium chocolates', 38.00, 'USD', '["chocolates"]'::jsonb, '["gift", "luxury", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000003', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Milk Chocolate Hearts', 'Heart-shaped milk chocolates - perfect chocolates for Valentine''s', 28.00, 'USD', '["chocolates"]'::jsonb, '["gift", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000004', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Hazelnut Praline Box', 'Crispy hazelnut praline chocolates - gourmet gift', 44.00, 'USD', '["chocolates"]'::jsonb, '["gift", "luxury", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000005', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Limo Wine Tour', 'Limo for winery tour - 6 hours luxury transport', 449.00, 'USD', '["limo"]'::jsonb, '["luxury", "night out", "travel", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000006', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Dine-In Movie Combo', 'Dinner and movie package - restaurant + movies', 65.00, 'USD', '["movies","restaurant"]'::jsonb, '["night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000007', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Jazz Night Tickets', 'Live jazz performance - intimate events venue', 45.00, 'USD', '["events"]'::jsonb, '["night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000008', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Italian Restaurant Dinner', 'Authentic Italian restaurant - pasta and wine for two', 95.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000009', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Sushi Omakase', 'Chef''s choice sushi - premium restaurant experience', 150.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000a', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Lavender & Eucalyptus', 'Calming lavender bouquet with eucalyptus - spa-style flowers', 48.00, 'USD', '["flowers"]'::jsonb, '["gift", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000b', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Caramel Sea Salt Chocolates', 'Salted caramel chocolates - decadent chocolates', 32.00, 'USD', '["chocolates"]'::jsonb, '["gift", "luxury", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000c', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Prom Night Limo', 'Limo for prom - 5 hours with red carpet', 399.00, 'USD', '["limo"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000d', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Date Night Movies Bundle', 'Two tickets + drinks - romantic movies outing', 42.00, 'USD', '["movies"]'::jsonb, '["night out", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000e', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Theater Show Tickets', 'Broadway-style theater - premium events', 89.00, 'USD', '["events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000f', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Steakhouse Dinner', 'Prime steak dinner for two - classic restaurant', 135.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, capabilities = EXCLUDED.capabilities, experience_tags = EXCLUDED.experience_tags, updated_at = NOW();

-- Partner 3: Luxe Rides
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, experience_tags, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000003-0001-4001-8001-000000000001', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Executive Sedan 2hr', 'Luxury sedan - limo service for business', 129.00, 'USD', '["limo"]'::jsonb, '["luxury", "travel"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000002', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Stretch Limo 6hr', 'Full-size stretch limo - weddings and events', 599.00, 'USD', '["limo"]'::jsonb, '["luxury", "night out", "travel", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000003', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'SUV Limo Party', 'Party SUV limo - 8 passengers', 349.00, 'USD', '["limo"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000004', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Limo Rose Upgrade', 'Fresh roses in limo - flowers add-on', 35.00, 'USD', '["flowers","limo"]'::jsonb, '["luxury", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000005', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Champagne & Chocolates', 'Champagne and chocolates in limo', 75.00, 'USD', '["chocolates","limo"]'::jsonb, '["luxury", "night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000006', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Limo to Movies', 'Limo round-trip to cinema - movies in style', 199.00, 'USD', '["limo","movies"]'::jsonb, '["luxury", "night out", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000007', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Concert Limo Package', 'Limo to concert - events transport', 279.00, 'USD', '["limo","events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000008', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Dinner & Limo Combo', 'Limo to restaurant and back - date night', 249.00, 'USD', '["limo","restaurant"]'::jsonb, '["luxury", "night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000009', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Hourly Limo Rental', 'Limo by the hour - flexible limo service', 99.00, 'USD', '["limo"]'::jsonb, '["luxury", "travel", "night out"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000a', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Wedding Limo Package', 'Bridal limo - 8 hours luxury limo', 799.00, 'USD', '["limo"]'::jsonb, '["luxury", "celebration", "travel"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000b', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Boutique Flower Arrangement', 'Elegant flowers for limo interior', 45.00, 'USD', '["flowers"]'::jsonb, '["luxury", "romantic", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000c', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Mini Chocolate Box', 'Premium chocolates for limo - 12 pieces', 25.00, 'USD', '["chocolates"]'::jsonb, '["gift", "romantic", "luxury"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000d', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Drive-In Movie Limo', 'Limo to drive-in movies - retro experience', 179.00, 'USD', '["limo","movies"]'::jsonb, '["night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000e', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Sports Event Limo', 'Limo to game or sports events', 329.00, 'USD', '["limo","events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000f', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Rooftop Restaurant Trip', 'Limo to rooftop restaurant - dinner and views', 189.00, 'USD', '["limo","restaurant"]'::jsonb, '["luxury", "night out", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, capabilities = EXCLUDED.capabilities, experience_tags = EXCLUDED.experience_tags, updated_at = NOW();

-- Partner 4: Cinema Plus
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, experience_tags, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000004-0001-4001-8001-000000000001', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Standard Movie Ticket', 'Single movie ticket - all movies', 14.99, 'USD', '["movies"]'::jsonb, '["night out"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000002', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Dolby Cinema Experience', 'Dolby Atmos movie - premium movies', 24.99, 'USD', '["movies"]'::jsonb, '["night out", "luxury", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000003', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Family Movie Pack', '4 tickets + popcorn - family movies', 59.99, 'USD', '["movies"]'::jsonb, '["family", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000004', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Movie Date Flowers', 'Small bouquet for movie date - flowers and movies', 29.99, 'USD', '["flowers","movies"]'::jsonb, '["romantic", "night out", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000005', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Cinema Candy Box', 'Movie theater chocolates and candy', 18.00, 'USD', '["chocolates","movies"]'::jsonb, '["night out", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000006', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'VIP Cinema + Limo', 'Luxury limo and VIP movie screening', 199.00, 'USD', '["limo","movies"]'::jsonb, '["luxury", "night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000007', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Film Festival Pass', 'Multi-day film festival - movies and events', 149.00, 'USD', '["movies","events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000008', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Dinner & Movie Combo', 'Restaurant meal + movie tickets', 79.00, 'USD', '["movies","restaurant"]'::jsonb, '["night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000009', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Matinee Special', 'Discount matinee movies - weekday', 9.99, 'USD', '["movies"]'::jsonb, '["night out", "family"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000a', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', '3D Movie Ticket', '3D movies experience', 19.99, 'USD', '["movies"]'::jsonb, '["night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000b', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Romantic Rose Single', 'Single rose for movie date - flowers', 12.00, 'USD', '["flowers"]'::jsonb, '["romantic", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000c', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Gourmet Popcorn + Chocolate', 'Premium popcorn with chocolates', 22.00, 'USD', '["chocolates"]'::jsonb, '["night out", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000d', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Midnight Screening', 'Special late-night movies event', 29.99, 'USD', '["movies","events"]'::jsonb, '["night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000e', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Cinema Bistro Dinner', 'In-theater restaurant dining', 45.00, 'USD', '["movies","restaurant"]'::jsonb, '["night out", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000f', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Classic Double Feature', 'Two movies back-to-back', 24.99, 'USD', '["movies"]'::jsonb, '["night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, capabilities = EXCLUDED.capabilities, experience_tags = EXCLUDED.experience_tags, updated_at = NOW();

-- Partner 5: Event Central
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, experience_tags, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000005-0001-4001-8001-000000000001', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Concert General Admission', 'Live concert tickets - music events', 65.00, 'USD', '["events"]'::jsonb, '["night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000002', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Comedy Club Night', 'Stand-up comedy show - fun events', 35.00, 'USD', '["events"]'::jsonb, '["night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000003', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Theater Musical Tickets', 'Broadway musical - premium events', 125.00, 'USD', '["events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000004', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Event VIP Flowers', 'VIP bouquet for events - backstage flowers', 75.00, 'USD', '["flowers","events"]'::jsonb, '["luxury", "celebration", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000005', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Backstage Chocolate Gift', 'Premium chocolates for artists - events gift', 55.00, 'USD', '["chocolates","events"]'::jsonb, '["luxury", "gift", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000006', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Event Limo Package', 'Limo to and from events venue', 249.00, 'USD', '["limo","events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000007', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Concert + After-Party', 'Concert ticket with after-party - events', 95.00, 'USD', '["events"]'::jsonb, '["night out", "celebration", "luxury"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000008', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Pre-Event Dinner', 'Restaurant dinner before events', 85.00, 'USD', '["events","restaurant"]'::jsonb, '["night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000009', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Festival Weekend Pass', '2-day festival - music and events', 199.00, 'USD', '["events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000a', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Wine Tasting Event', 'Wine tasting and vineyard events', 55.00, 'USD', '["events"]'::jsonb, '["night out", "celebration", "luxury"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000b', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Celebration Bouquet', 'Party flowers for events', 49.00, 'USD', '["flowers"]'::jsonb, '["celebration", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000c', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Event Gift Chocolates', 'Elegant chocolates for event gifting', 38.00, 'USD', '["chocolates"]'::jsonb, '["gift", "celebration", "luxury"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000d', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Symphony Orchestra', 'Classical symphony events', 75.00, 'USD', '["events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000e', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Rooftop Event Dinner', 'Dinner at rooftop events venue', 120.00, 'USD', '["events","restaurant"]'::jsonb, '["luxury", "night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000f', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Magic Show Tickets', 'Family magic show - events for all ages', 28.00, 'USD', '["events"]'::jsonb, '["family", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, capabilities = EXCLUDED.capabilities, experience_tags = EXCLUDED.experience_tags, updated_at = NOW();

-- Partner 6: Gourmet Bites
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, experience_tags, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000006-0001-4001-8001-000000000001', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Chef''s Table Experience', 'Exclusive chef''s table - fine dining restaurant', 250.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000002', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Romantic Candlelit Dinner', 'Intimate restaurant dinner for two', 145.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000003', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Sunday Brunch for Four', 'Brunch at top restaurant - mimosas included', 180.00, 'USD', '["restaurant"]'::jsonb, '["celebration", "family", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000004', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Table Flowers Upgrade', 'Fresh flowers for restaurant table', 40.00, 'USD', '["flowers","restaurant"]'::jsonb, '["romantic", "celebration", "luxury"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000005', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Dessert Chocolates', 'Artisan chocolates with dessert - restaurant add-on', 25.00, 'USD', '["chocolates","restaurant"]'::jsonb, '["luxury", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000006', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Dinner Limo Package', 'Limo to restaurant - date night', 199.00, 'USD', '["limo","restaurant"]'::jsonb, '["luxury", "night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000007', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Dinner & Movie Date', 'Restaurant + movies - complete date', 95.00, 'USD', '["restaurant","movies"]'::jsonb, '["night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000008', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Concert Dinner Package', 'Pre-concert restaurant dinner', 165.00, 'USD', '["restaurant","events"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000009', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Sushi Omakase for Two', 'Omakase at top sushi restaurant', 320.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000a', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Tapas & Wine Tasting', 'Spanish tapas restaurant experience', 85.00, 'USD', '["restaurant"]'::jsonb, '["night out", "romantic", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000b', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Anniversary Rose Centerpiece', 'Roses for restaurant table - flowers', 55.00, 'USD', '["flowers"]'::jsonb, '["romantic", "celebration", "luxury"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000c', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'After-Dinner Chocolates', 'Petit fours and chocolates - restaurant finale', 18.00, 'USD', '["chocolates"]'::jsonb, '["luxury", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000d', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Farm-to-Table Dinner', 'Seasonal farm-to-table restaurant', 110.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000e', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Private Dining Room', 'Private room at restaurant - up to 8 guests', 500.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000f', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Wine Pairing Dinner', '5-course with wine pairing - restaurant', 175.00, 'USD', '["restaurant"]'::jsonb, '["luxury", "night out", "romantic"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, capabilities = EXCLUDED.capabilities, experience_tags = EXCLUDED.experience_tags, updated_at = NOW();

-- Partner 7: Tots Trunk - baby/newborn + pre-bundled products (bundle-in-bundle testing)
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, experience_tags, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000007-0001-4001-8001-000000000001', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Newborn Onesie Set', '5-pack organic cotton onesies - newborn essentials', 34.99, 'USD', '["baby","newborn"]'::jsonb, '["baby", "gift", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-000000000002', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Swaddle Blankets Pack', '4 muslin swaddle blankets - newborn sleep', 29.99, 'USD', '["baby","newborn"]'::jsonb, '["baby", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-000000000003', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Glass Baby Bottles Set', '4 BPA-free glass bottles with nipples - newborn feeding', 42.00, 'USD', '["baby","newborn"]'::jsonb, '["baby", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-000000000004', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Newborn Diaper Pack', '120 count newborn diapers - hypoallergenic', 44.99, 'USD', '["baby","newborn"]'::jsonb, '["baby"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-000000000005', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Baby Wipes Sensitive', '8-pack fragrance-free wipes - newborn care', 24.99, 'USD', '["baby","newborn"]'::jsonb, '["baby"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-000000000006', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Pacifier Set', '6-pack orthodontic pacifiers - newborn soothing', 18.99, 'USD', '["baby","newborn"]'::jsonb, '["baby", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-000000000007', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Burp Cloths 6-Pack', 'Absorbent burp cloths - newborn feeding', 22.00, 'USD', '["baby","newborn"]'::jsonb, '["baby"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-000000000008', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Baby Bibs Set', '5 silicone bibs - newborn and infant feeding', 19.99, 'USD', '["baby","newborn"]'::jsonb, '["baby", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-000000000009', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Newborn Essentials Kit', 'Pre-bundled: onesies, swaddles, bottles, diapers, wipes - complete newborn starter', 149.99, 'USD', '["baby","newborn","bundle"]'::jsonb, '["baby", "gift", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-00000000000a', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Baby Shower Gift Bundle', 'Pre-bundled: blanket, onesie set, bibs, burp cloths - perfect baby shower gift', 89.99, 'USD', '["baby","gifts","bundle"]'::jsonb, '["baby", "gift", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-00000000000b', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'First 6 Months Starter Kit', 'Pre-bundled: diapers, wipes, bottles, pacifiers, bibs - first six months covered', 129.99, 'USD', '["baby","bundle"]'::jsonb, '["baby", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-00000000000c', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Hospital Go-Bag', 'Pre-bundled: onesies, swaddles, diapers, wipes - ready for hospital discharge', 79.99, 'USD', '["baby","newborn","bundle"]'::jsonb, '["baby", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-00000000000d', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Nursery Starter Set', 'Pre-bundled: crib sheets, swaddles, blankets - nursery essentials', 99.99, 'USD', '["baby","newborn","bundle"]'::jsonb, '["baby", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-00000000000e', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Welcome Home Baby Bundle', 'Pre-bundled: full newborn kit + gift wrap - welcome baby home', 199.99, 'USD', '["baby","newborn","gifts","bundle"]'::jsonb, '["baby", "gift", "celebration"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000007-0001-4001-8001-00000000000f', 'a1000007-9c0b-4ef8-bb6d-6bb9bd380a07', 'Baby Care Combo', 'Pre-bundled: wipes, diapers, lotion, shampoo - daily care essentials', 59.99, 'USD', '["baby","bundle"]'::jsonb, '["baby", "gift"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, capabilities = EXCLUDED.capabilities, experience_tags = EXCLUDED.experience_tags, updated_at = NOW();

-- =============================================================================
-- Phase 2 scenario: Task Queue, Hub/Negotiator, Hybrid Response test data
-- Second vendor (Chocolate Co.), Hub partner, sample bundle + order for real-life flow.
-- See docs/archive/REAL_LIFE_TEST_SCENARIO.md for the test flow (if present).
-- =============================================================================

-- Flower Co. Demo (referenced by bundle_legs)
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES (
  'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'Flower Co. Demo',
  'retail',
  'flowers@example.com',
  'approved',
  90,
  true,
  NOW(),
  NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Chocolate Co. Demo
INSERT INTO partners (id, user_id, business_name, business_type, contact_email, verification_status, trust_score, is_active, created_at, updated_at)
VALUES (
  'b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a23',
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
  'Chocolate Co. Demo',
  'retail',
  'chocolate@example.com',
  'approved',
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
  'approved',
  90,
  true,
  NOW(),
  NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Flower product (for Phase 2 bundle)
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, experience_tags, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at)
VALUES (
  'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33',
  'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
  'Demo Rose Bouquet',
  'Classic roses for scenario testing',
  49.99,
  'USD',
  '["flowers"]'::jsonb,
  '["gift", "celebration", "romantic"]'::jsonb,
  true,
  true,
  'in_stock',
  NOW(),
  NOW()
)
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, capabilities = EXCLUDED.capabilities, experience_tags = EXCLUDED.experience_tags, updated_at = NOW();

-- Chocolate product (Phase 2)
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, experience_tags, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at)
VALUES (
  'c3eebc99-9c0b-4ef8-bb6d-6bb9bd380a34',
  'b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a23',
  'Premium Chocolates',
  'Assorted gourmet chocolates',
  29.99,
  'USD',
  '["chocolates"]'::jsonb,
  '["gift", "celebration", "luxury", "romantic"]'::jsonb,
  true,
  true,
  'in_stock',
  NOW(),
  NOW()
)
ON CONFLICT (id) DO UPDATE SET description = EXCLUDED.description, experience_tags = EXCLUDED.experience_tags, updated_at = NOW();

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

-- Bundle legs (flowers first, chocolates second)
INSERT INTO bundle_legs (id, bundle_id, product_id, partner_id, leg_sequence, leg_type, price, created_at)
VALUES
  ('d2eebc99-9c0b-4ef8-bb6d-6bb9bd380a41', 'd1eebc99-9c0b-4ef8-bb6d-6bb9bd380a40', 'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 1, 'product', 49.99, NOW()),
  ('d3eebc99-9c0b-4ef8-bb6d-6bb9bd380a42', 'd1eebc99-9c0b-4ef8-bb6d-6bb9bd380a40', 'c3eebc99-9c0b-4ef8-bb6d-6bb9bd380a34', 'b2eebc99-9c0b-4ef8-bb6d-6bb9bd380a23', 2, 'product', 29.99, NOW())
ON CONFLICT (id) DO NOTHING;

-- Order (Phase 2 scenario)
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

COMMIT;
