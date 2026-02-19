-- Migration: OrchestrationTrace for product discovery and bundle creation
-- Records relevance_score, admin_weight, protocol per product
-- Date: 2025-01-28

BEGIN;

CREATE TABLE IF NOT EXISTS orchestration_traces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_type TEXT NOT NULL CHECK (trace_type IN ('product_discovery', 'bundle_created')),
  thread_id UUID REFERENCES chat_threads(id) ON DELETE SET NULL,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  query TEXT,
  experience_name TEXT,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orchestration_traces_type ON orchestration_traces(trace_type);
CREATE INDEX IF NOT EXISTS idx_orchestration_traces_thread ON orchestration_traces(thread_id);
CREATE INDEX IF NOT EXISTS idx_orchestration_traces_created ON orchestration_traces(created_at DESC);

COMMENT ON TABLE orchestration_traces IS 'Trace of product discovery and bundle creation: relevance_score, admin_weight, protocol per product';
COMMENT ON COLUMN orchestration_traces.metadata IS 'products: [{product_id, partner_id, protocol, relevance_score, admin_weight}], options for bundle_created';

COMMIT;
