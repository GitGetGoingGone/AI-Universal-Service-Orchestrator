-- Migration: Core tables + Scout Engine (Modules 1, 9)
-- Date: 2024-01-28
-- Dependencies: extensions

BEGIN;

-- Users (Clerk integration)
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT,
  phone_number TEXT,
  legal_name TEXT,
  display_name TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone_number);

-- Capability tags taxonomy (Module 7)
CREATE TABLE capability_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tag_name VARCHAR(100) NOT NULL UNIQUE,
  tag_category VARCHAR(50),
  description TEXT,
  parent_tag_id UUID REFERENCES capability_tags(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_capability_tags_name ON capability_tags(tag_name);
CREATE INDEX idx_capability_tags_category ON capability_tags(tag_category);

-- Partners (Module 9)
CREATE TABLE partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  business_name TEXT NOT NULL,
  business_type VARCHAR(50),
  tax_id VARCHAR(50),
  legal_entity_name TEXT,
  contact_email TEXT NOT NULL,
  contact_phone TEXT,
  address JSONB,
  verification_status VARCHAR(20) DEFAULT 'pending',
  trust_score INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  verified_at TIMESTAMPTZ
);

CREATE INDEX idx_partners_user_id ON partners(user_id);
CREATE INDEX idx_partners_verification_status ON partners(verification_status);
CREATE INDEX idx_partners_trust_score ON partners(trust_score DESC);
CREATE INDEX idx_partners_is_active ON partners(is_active);

-- Products (Module 1)
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  capabilities JSONB,
  metadata JSONB,
  manifest_url TEXT,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_products_partner_id ON products(partner_id);
CREATE INDEX idx_products_capabilities ON products USING GIN(capabilities);
CREATE INDEX idx_products_name_search ON products USING GIN(to_tsvector('english', name));
-- ivfflat for semantic search; consider lists=sqrt(row_count) after data load
CREATE INDEX idx_products_embedding ON products USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_products_created_at ON products(created_at DESC);
CREATE INDEX idx_products_deleted_at ON products(deleted_at) WHERE deleted_at IS NULL;

COMMENT ON TABLE products IS 'Product catalog from all partners';

-- Product capabilities junction
CREATE TABLE product_capabilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  capability_tag VARCHAR(100) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, capability_tag)
);

CREATE INDEX idx_product_capabilities_product_id ON product_capabilities(product_id);
CREATE INDEX idx_product_capabilities_tag ON product_capabilities(capability_tag);

-- Partner manifests cache
CREATE TABLE partner_manifests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
  manifest_url TEXT NOT NULL,
  manifest_type VARCHAR(20) NOT NULL,
  manifest_data JSONB NOT NULL,
  cached_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  last_validated_at TIMESTAMPTZ,
  validation_status VARCHAR(20) DEFAULT 'pending'
);

CREATE INDEX idx_partner_manifests_partner_id ON partner_manifests(partner_id);
CREATE INDEX idx_partner_manifests_expires_at ON partner_manifests(expires_at);

-- Manifest cache metadata
CREATE TABLE manifest_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manifest_url TEXT NOT NULL UNIQUE,
  etag TEXT,
  last_modified TIMESTAMPTZ,
  cache_ttl INTEGER DEFAULT 3600,
  cached_at TIMESTAMPTZ DEFAULT NOW(),
  hit_count INTEGER DEFAULT 0,
  last_hit_at TIMESTAMPTZ
);

CREATE INDEX idx_manifest_cache_url ON manifest_cache(manifest_url);

COMMIT;
