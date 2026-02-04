-- Migration: Intent Resolver + Bundles (Modules 4, 7)
-- Date: 2024-01-28
-- Dependencies: core_and_scout

BEGIN;

-- Intents (Module 4)
CREATE TABLE intents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  original_text TEXT NOT NULL,
  intent_type VARCHAR(50),
  status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_intents_user_id ON intents(user_id);
CREATE INDEX idx_intents_status ON intents(status);
CREATE INDEX idx_intents_created_at ON intents(created_at DESC);

-- Intent graphs
CREATE TABLE intent_graphs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  intent_id UUID REFERENCES intents(id) ON DELETE CASCADE,
  graph_data JSONB NOT NULL,
  entities JSONB,
  confidence_score DECIMAL(3,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_intent_graphs_intent_id ON intent_graphs(intent_id);
CREATE INDEX idx_intent_graphs_graph_data ON intent_graphs USING GIN(graph_data);

-- Intent entities
CREATE TABLE intent_entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  intent_id UUID REFERENCES intents(id) ON DELETE CASCADE,
  entity_type VARCHAR(50) NOT NULL,
  entity_value TEXT NOT NULL,
  confidence DECIMAL(3,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_intent_entities_intent_id ON intent_entities(intent_id);
CREATE INDEX idx_intent_entities_type ON intent_entities(entity_type);

-- Premium products (Module 7)
CREATE TABLE premium_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_name VARCHAR(100) NOT NULL,
  product_name TEXT NOT NULL,
  product_type VARCHAR(50) NOT NULL,
  base_price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  description TEXT,
  images JSONB,
  specifications JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_premium_products_brand ON premium_products(brand_name);
CREATE INDEX idx_premium_products_type ON premium_products(product_type);

-- Product to capability mappings
CREATE TABLE product_capability_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  capability_tag_id UUID REFERENCES capability_tags(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, capability_tag_id)
);

CREATE INDEX idx_product_capability_mappings_product ON product_capability_mappings(product_id);
CREATE INDEX idx_product_capability_mappings_tag ON product_capability_mappings(capability_tag_id);

-- Bundles
CREATE TABLE bundles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  intent_id UUID REFERENCES intents(id),
  bundle_name TEXT,
  total_price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'draft',
  visibility_mode VARCHAR(20) DEFAULT 'transparent',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  confirmed_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_bundles_user_id ON bundles(user_id);
CREATE INDEX idx_bundles_status ON bundles(status);
CREATE INDEX idx_bundles_created_at ON bundles(created_at DESC);

-- Bundle legs
CREATE TABLE bundle_legs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES bundles(id) ON DELETE CASCADE,
  leg_sequence INTEGER NOT NULL,
  product_id UUID REFERENCES products(id),
  partner_id UUID REFERENCES partners(id),
  leg_type VARCHAR(50) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  customization_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bundle_legs_bundle_id ON bundle_legs(bundle_id);
CREATE INDEX idx_bundle_legs_sequence ON bundle_legs(bundle_id, leg_sequence);

COMMIT;
