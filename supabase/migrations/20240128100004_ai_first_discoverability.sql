-- Migration: AI-First Discoverability (Module 3)
-- Manifest template, action models, offline discovery strategy
-- Dependencies: core_and_scout

BEGIN;

-- Action models for AI agents (Pillar 3)
CREATE TABLE agent_action_models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action_name VARCHAR(100) UNIQUE NOT NULL,
  method VARCHAR(10) NOT NULL,
  endpoint VARCHAR(255) NOT NULL,
  requires_auth BOOLEAN DEFAULT TRUE,
  requires_approval_if_over DECIMAL(10,2),
  rate_limit_per_hour INTEGER,
  allowed_parameters JSONB,
  restricted_parameters JSONB,
  allowed_modifications JSONB,
  restricted_modifications JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_action_models_action_name ON agent_action_models(action_name);
CREATE INDEX idx_agent_action_models_is_active ON agent_action_models(is_active);

-- Platform manifest config (for offline discovery / static manifest)
CREATE TABLE platform_manifest_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manifest_version VARCHAR(20) NOT NULL DEFAULT '1.0',
  platform_id VARCHAR(100) NOT NULL DEFAULT 'uso-orchestrator',
  platform_name VARCHAR(255) NOT NULL DEFAULT 'AI Universal Service Orchestrator',
  discovery_endpoint VARCHAR(500),
  capabilities JSONB DEFAULT '{}',
  product_schema JSONB DEFAULT '{}',
  offline_discovery JSONB DEFAULT '{"enabled": true, "cache_ttl": 3600}',
  webhook_endpoints JSONB DEFAULT '{}',
  supported_regions JSONB DEFAULT '["US", "CA"]',
  max_order_value DECIMAL(10,2) DEFAULT 10000.00,
  currency VARCHAR(3) DEFAULT 'USD',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_platform_manifest_config_active ON platform_manifest_config(id) WHERE is_active = TRUE;

COMMENT ON TABLE agent_action_models IS 'Module 3: Action models for AI agents - allowed operations, rate limits, approval thresholds';
COMMENT ON TABLE platform_manifest_config IS 'Module 3: Platform manifest for AI-first discoverability';

-- RLS: public read for AI agent discovery (anon can read manifest)
ALTER TABLE agent_action_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_manifest_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY agent_action_models_select ON agent_action_models FOR SELECT USING (is_active = TRUE);
CREATE POLICY platform_manifest_config_select ON platform_manifest_config FOR SELECT USING (is_active = TRUE);

-- Seed default action models
INSERT INTO agent_action_models (
  action_name, method, endpoint, requires_auth, requires_approval_if_over, rate_limit_per_hour,
  allowed_parameters, is_active
) VALUES
  ('discover_products', 'POST', '/api/v1/chat', FALSE, NULL, 100,
   '{"text": "string (required)", "limit": "integer (optional)"}'::jsonb, TRUE),
  ('create_order', 'POST', '/api/v1/orders', TRUE, 200.00, 50,
   '{"bundle_id": "uuid (required)", "delivery_address": "object (required)"}'::jsonb, TRUE),
  ('modify_order', 'PATCH', '/api/v1/orders/{id}', TRUE, NULL, 30,
   '{}'::jsonb, TRUE),
  ('cancel_order', 'DELETE', '/api/v1/orders/{id}', TRUE, NULL, 20,
   '{}'::jsonb, TRUE),
  ('track_order', 'GET', '/api/v1/orders/{id}/status', TRUE, NULL, 60,
   '{}'::jsonb, TRUE);

-- Seed default platform manifest config
INSERT INTO platform_manifest_config (
  manifest_version, platform_id, platform_name,
  discovery_endpoint, capabilities, offline_discovery, supported_regions
) VALUES (
  '1.0', 'uso-orchestrator', 'AI Universal Service Orchestrator',
  '/api/v1/chat',
  '{"can_initiate_checkout": true, "can_modify_order": false, "can_cancel_order": true, "requires_human_approval_over": 200.00}'::jsonb,
  '{"enabled": true, "cache_ttl": 3600, "update_frequency": "hourly"}'::jsonb,
  '["US", "CA"]'::jsonb
);

COMMIT;
