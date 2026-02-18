-- Seed: 6 test partners with synthetic products (flowers, chocolates, limos, movies, events, restaurant)
-- Run after migrations and seed.sql. Each partner has ~15 products across 6 categories, approved for testing.

BEGIN;

-- Ensure capability tags exist
INSERT INTO capability_tags (tag_name, tag_category, description) VALUES
  ('flowers', 'product', 'Fresh flowers and bouquets'),
  ('chocolates', 'product', 'Custom and premium chocolates'),
  ('limo', 'service', 'Luxury limousine transport'),
  ('movies', 'service', 'Movie tickets and cinema'),
  ('events', 'service', 'Concerts, shows, and events'),
  ('restaurant', 'service', 'Restaurant reservations and dining')
ON CONFLICT (tag_name) DO NOTHING;

-- Test user for partners
INSERT INTO users (id, email, legal_name, display_name, created_at, updated_at)
VALUES ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'dev@example.com', 'Dev User', 'Dev', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

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

-- Products: 15 per partner across 6 categories (2-3 per category)
-- Partner 1: Bloom & Petals
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000001-0001-4001-8001-000000000001', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Classic Red Roses', 'A dozen fresh red roses - perfect for anniversaries and romance', 59.99, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000002', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Mixed Spring Bouquet', 'Colorful mix of tulips, daisies, and lilies - flowers for any occasion', 45.00, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000003', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Premium Orchid Arrangement', 'Elegant orchid plant - luxury flowers for gifting', 89.99, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000004', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Belgian Chocolate Box', 'Assorted premium Belgian chocolates - 24 pieces', 34.99, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000005', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Truffle Sampler', 'Gourmet dark and milk chocolate truffles - chocolates for date night', 42.00, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000006', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Limo 4-Hour Package', 'Luxury limo for 4 hours - perfect for date night or events', 299.00, 'USD', '["limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000007', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Stretch Limo Airport Transfer', 'Premium limo airport pickup or drop-off', 149.00, 'USD', '["limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000008', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Movie Night Duo Pass', 'Two movie tickets with popcorn and drinks', 35.00, 'USD', '["movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-000000000009', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'IMAX Premium Experience', 'IMAX movie tickets for two - best movies experience', 48.00, 'USD', '["movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000a', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Concert VIP Package', 'VIP access to live concert - events and entertainment', 199.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000b', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Comedy Show Tickets', 'Two tickets to stand-up comedy show - fun events', 55.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000c', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Romantic Dinner for Two', '3-course dinner at upscale restaurant - reservation included', 120.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000d', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Brunch Experience', 'Sunday brunch for two at top-rated restaurant', 75.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000e', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Chef''s Tasting Menu', '5-course tasting menu - fine dining restaurant experience', 185.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000001-0001-4001-8001-00000000000f', 'a1000001-9c0b-4ef8-bb6d-6bb9bd380a01', 'Sunflower Bouquet', 'Bright sunflowers - cheerful flowers for any day', 39.99, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, updated_at = NOW();

-- Partner 2: Sweet Treats Co
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000002-0001-4001-8001-000000000001', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Birthday Flower Bouquet', 'Colorful birthday flowers with balloon', 52.00, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000002', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Dark Chocolate Collection', 'Artisan dark chocolates - 16 pieces premium chocolates', 38.00, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000003', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Milk Chocolate Hearts', 'Heart-shaped milk chocolates - perfect chocolates for Valentine''s', 28.00, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000004', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Hazelnut Praline Box', 'Crispy hazelnut praline chocolates - gourmet gift', 44.00, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000005', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Limo Wine Tour', 'Limo for winery tour - 6 hours luxury transport', 449.00, 'USD', '["limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000006', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Dine-In Movie Combo', 'Dinner and movie package - restaurant + movies', 65.00, 'USD', '["movies","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000007', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Jazz Night Tickets', 'Live jazz performance - intimate events venue', 45.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000008', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Italian Restaurant Dinner', 'Authentic Italian restaurant - pasta and wine for two', 95.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-000000000009', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Sushi Omakase', 'Chef''s choice sushi - premium restaurant experience', 150.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000a', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Lavender & Eucalyptus', 'Calming lavender bouquet with eucalyptus - spa-style flowers', 48.00, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000b', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Caramel Sea Salt Chocolates', 'Salted caramel chocolates - decadent chocolates', 32.00, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000c', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Prom Night Limo', 'Limo for prom - 5 hours with red carpet', 399.00, 'USD', '["limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000d', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Date Night Movies Bundle', 'Two tickets + drinks - romantic movies outing', 42.00, 'USD', '["movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000e', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Theater Show Tickets', 'Broadway-style theater - premium events', 89.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000002-0001-4001-8001-00000000000f', 'a1000002-9c0b-4ef8-bb6d-6bb9bd380a02', 'Steakhouse Dinner', 'Prime steak dinner for two - classic restaurant', 135.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, updated_at = NOW();

-- Partner 3: Luxe Rides
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000003-0001-4001-8001-000000000001', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Executive Sedan 2hr', 'Luxury sedan - limo service for business', 129.00, 'USD', '["limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000002', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Stretch Limo 6hr', 'Full-size stretch limo - weddings and events', 599.00, 'USD', '["limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000003', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'SUV Limo Party', 'Party SUV limo - 8 passengers', 349.00, 'USD', '["limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000004', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Limo Rose Upgrade', 'Fresh roses in limo - flowers add-on', 35.00, 'USD', '["flowers","limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000005', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Champagne & Chocolates', 'Champagne and chocolates in limo', 75.00, 'USD', '["chocolates","limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000006', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Limo to Movies', 'Limo round-trip to cinema - movies in style', 199.00, 'USD', '["limo","movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000007', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Concert Limo Package', 'Limo to concert - events transport', 279.00, 'USD', '["limo","events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000008', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Dinner & Limo Combo', 'Limo to restaurant and back - date night', 249.00, 'USD', '["limo","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-000000000009', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Hourly Limo Rental', 'Limo by the hour - flexible limo service', 99.00, 'USD', '["limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000a', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Wedding Limo Package', 'Bridal limo - 8 hours luxury limo', 799.00, 'USD', '["limo"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000b', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Boutique Flower Arrangement', 'Elegant flowers for limo interior', 45.00, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000c', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Mini Chocolate Box', 'Premium chocolates for limo - 12 pieces', 25.00, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000d', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Drive-In Movie Limo', 'Limo to drive-in movies - retro experience', 179.00, 'USD', '["limo","movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000e', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Sports Event Limo', 'Limo to game or sports events', 329.00, 'USD', '["limo","events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000003-0001-4001-8001-00000000000f', 'a1000003-9c0b-4ef8-bb6d-6bb9bd380a03', 'Rooftop Restaurant Trip', 'Limo to rooftop restaurant - dinner and views', 189.00, 'USD', '["limo","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, updated_at = NOW();

-- Partner 4: Cinema Plus
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000004-0001-4001-8001-000000000001', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Standard Movie Ticket', 'Single movie ticket - all movies', 14.99, 'USD', '["movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000002', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Dolby Cinema Experience', 'Dolby Atmos movie - premium movies', 24.99, 'USD', '["movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000003', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Family Movie Pack', '4 tickets + popcorn - family movies', 59.99, 'USD', '["movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000004', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Movie Date Flowers', 'Small bouquet for movie date - flowers and movies', 29.99, 'USD', '["flowers","movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000005', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Cinema Candy Box', 'Movie theater chocolates and candy', 18.00, 'USD', '["chocolates","movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000006', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'VIP Cinema + Limo', 'Luxury limo and VIP movie screening', 199.00, 'USD', '["limo","movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000007', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Film Festival Pass', 'Multi-day film festival - movies and events', 149.00, 'USD', '["movies","events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000008', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Dinner & Movie Combo', 'Restaurant meal + movie tickets', 79.00, 'USD', '["movies","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-000000000009', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Matinee Special', 'Discount matinee movies - weekday', 9.99, 'USD', '["movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000a', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', '3D Movie Ticket', '3D movies experience', 19.99, 'USD', '["movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000b', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Romantic Rose Single', 'Single rose for movie date - flowers', 12.00, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000c', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Gourmet Popcorn + Chocolate', 'Premium popcorn with chocolates', 22.00, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000d', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Midnight Screening', 'Special late-night movies event', 29.99, 'USD', '["movies","events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000e', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Cinema Bistro Dinner', 'In-theater restaurant dining', 45.00, 'USD', '["movies","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000004-0001-4001-8001-00000000000f', 'a1000004-9c0b-4ef8-bb6d-6bb9bd380a04', 'Classic Double Feature', 'Two movies back-to-back', 24.99, 'USD', '["movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, updated_at = NOW();

-- Partner 5: Event Central
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000005-0001-4001-8001-000000000001', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Concert General Admission', 'Live concert tickets - music events', 65.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000002', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Comedy Club Night', 'Stand-up comedy show - fun events', 35.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000003', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Theater Musical Tickets', 'Broadway musical - premium events', 125.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000004', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Event VIP Flowers', 'VIP bouquet for events - backstage flowers', 75.00, 'USD', '["flowers","events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000005', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Backstage Chocolate Gift', 'Premium chocolates for artists - events gift', 55.00, 'USD', '["chocolates","events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000006', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Event Limo Package', 'Limo to and from events venue', 249.00, 'USD', '["limo","events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000007', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Concert + After-Party', 'Concert ticket with after-party - events', 95.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000008', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Pre-Event Dinner', 'Restaurant dinner before events', 85.00, 'USD', '["events","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-000000000009', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Festival Weekend Pass', '2-day festival - music and events', 199.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000a', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Wine Tasting Event', 'Wine tasting and vineyard events', 55.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000b', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Celebration Bouquet', 'Party flowers for events', 49.00, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000c', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Event Gift Chocolates', 'Elegant chocolates for event gifting', 38.00, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000d', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Symphony Orchestra', 'Classical symphony events', 75.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000e', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Rooftop Event Dinner', 'Dinner at rooftop events venue', 120.00, 'USD', '["events","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000005-0001-4001-8001-00000000000f', 'a1000005-9c0b-4ef8-bb6d-6bb9bd380a05', 'Magic Show Tickets', 'Family magic show - events for all ages', 28.00, 'USD', '["events"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, updated_at = NOW();

-- Partner 6: Gourmet Bites
INSERT INTO products (id, partner_id, name, description, price, currency, capabilities, is_eligible_search, is_eligible_checkout, availability, created_at, updated_at) VALUES
  ('a1000006-0001-4001-8001-000000000001', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Chef''s Table Experience', 'Exclusive chef''s table - fine dining restaurant', 250.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000002', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Romantic Candlelit Dinner', 'Intimate restaurant dinner for two', 145.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000003', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Sunday Brunch for Four', 'Brunch at top restaurant - mimosas included', 180.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000004', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Table Flowers Upgrade', 'Fresh flowers for restaurant table', 40.00, 'USD', '["flowers","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000005', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Dessert Chocolates', 'Artisan chocolates with dessert - restaurant add-on', 25.00, 'USD', '["chocolates","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000006', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Dinner Limo Package', 'Limo to restaurant - date night', 199.00, 'USD', '["limo","restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000007', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Dinner & Movie Date', 'Restaurant + movies - complete date', 95.00, 'USD', '["restaurant","movies"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000008', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Concert Dinner Package', 'Pre-concert restaurant dinner', 165.00, 'USD', '["restaurant","events"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-000000000009', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Sushi Omakase for Two', 'Omakase at top sushi restaurant', 320.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000a', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Tapas & Wine Tasting', 'Spanish tapas restaurant experience', 85.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000b', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Anniversary Rose Centerpiece', 'Roses for restaurant table - flowers', 55.00, 'USD', '["flowers"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000c', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'After-Dinner Chocolates', 'Petit fours and chocolates - restaurant finale', 18.00, 'USD', '["chocolates"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000d', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Farm-to-Table Dinner', 'Seasonal farm-to-table restaurant', 110.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000e', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Private Dining Room', 'Private room at restaurant - up to 8 guests', 500.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW()),
  ('a1000006-0001-4001-8001-00000000000f', 'a1000006-9c0b-4ef8-bb6d-6bb9bd380a06', 'Wine Pairing Dinner', '5-course with wine pairing - restaurant', 175.00, 'USD', '["restaurant"]'::jsonb, true, true, 'in_stock', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, price = EXCLUDED.price, updated_at = NOW();

COMMIT;
