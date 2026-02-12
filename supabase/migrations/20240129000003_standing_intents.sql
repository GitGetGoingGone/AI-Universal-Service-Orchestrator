-- Migration: Standing Intents (Module 23)
-- Dependencies: core_and_scout, link_account_support
-- Month 0 Integration Hub: wait_for_external_event(UserApproval)

BEGIN;

CREATE TABLE IF NOT EXISTS standing_intents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  intent_description TEXT NOT NULL,
  intent_conditions JSONB DEFAULT '{}',
  orchestration_instance_id VARCHAR(255) UNIQUE NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  requires_approval BOOLEAN DEFAULT TRUE,
  approval_timeout_hours INTEGER DEFAULT 24,
  platform VARCHAR(50),
  thread_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ
);

CREATE INDEX idx_standing_intents_user_id ON standing_intents(user_id);
CREATE INDEX idx_standing_intents_status ON standing_intents(status);
CREATE INDEX idx_standing_intents_instance ON standing_intents(orchestration_instance_id);

CREATE TABLE IF NOT EXISTS standing_intent_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  standing_intent_id UUID REFERENCES standing_intents(id) ON DELETE CASCADE,
  log_type VARCHAR(50) NOT NULL,
  narrative TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_standing_intent_logs_intent ON standing_intent_logs(standing_intent_id);

COMMENT ON TABLE standing_intents IS 'Module 23: Standing intents with Durable Functions orchestration';
COMMENT ON TABLE standing_intent_logs IS 'Module 23: Standing intent progress logs';

COMMIT;
