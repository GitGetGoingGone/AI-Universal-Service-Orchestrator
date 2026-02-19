-- Migration: Partner Representation Rules
-- Phase 1: Protocol-Aware Orchestrator - Partner weighting and protocol preference
-- Date: 2025-01-28
-- Dependencies: partners

BEGIN;

CREATE TABLE IF NOT EXISTS partner_representation_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  admin_weight DECIMAL(5,2) DEFAULT 1.0 CHECK (admin_weight >= 0 AND admin_weight <= 10.0),
  preferred_protocol TEXT DEFAULT 'DB' CHECK (preferred_protocol IN ('UCP', 'MCP', 'DB')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(partner_id)
);

CREATE INDEX IF NOT EXISTS idx_partner_representation_rules_partner ON partner_representation_rules(partner_id);
CREATE INDEX IF NOT EXISTS idx_partner_representation_rules_protocol ON partner_representation_rules(preferred_protocol);

COMMENT ON TABLE partner_representation_rules IS 'Admin weight and protocol preference per partner for Partner Balancer';
COMMENT ON COLUMN partner_representation_rules.admin_weight IS 'Multiplier for relevance (1.0=neutral, >1=boost, <1=reduce)';
COMMENT ON COLUMN partner_representation_rules.preferred_protocol IS 'UCP=manifest, MCP=model context, DB=local database';

COMMIT;
