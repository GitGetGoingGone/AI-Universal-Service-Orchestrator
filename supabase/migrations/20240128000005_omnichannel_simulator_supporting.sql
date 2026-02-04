-- Migration: Omnichannel, Partner Simulator, Supporting tables (Modules 24, 25)
-- Date: 2024-01-28
-- Dependencies: timechain_recovery_support

BEGIN;

-- Negotiations (Module 24)
CREATE TABLE negotiations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  order_leg_id UUID REFERENCES order_legs(id),
  partner_id UUID REFERENCES partners(id),
  negotiation_type VARCHAR(50) NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  channel VARCHAR(20) NOT NULL,
  counter_offer_count INTEGER DEFAULT 0,
  timeout_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  responded_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_negotiations_order_id ON negotiations(order_id);
CREATE INDEX idx_negotiations_partner_id ON negotiations(partner_id);
CREATE INDEX idx_negotiations_status ON negotiations(status);

-- Negotiation messages
CREATE TABLE negotiation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  negotiation_id UUID REFERENCES negotiations(id) ON DELETE CASCADE,
  message_type VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  channel VARCHAR(20) NOT NULL,
  channel_message_id TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_negotiation_messages_negotiation_id ON negotiation_messages(negotiation_id);

-- Communication preferences
CREATE TABLE communication_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
  channel VARCHAR(20) NOT NULL,
  channel_identifier TEXT NOT NULL,
  is_preferred BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(partner_id, channel)
);

CREATE INDEX idx_communication_preferences_partner_id ON communication_preferences(partner_id);

-- Escalations
CREATE TABLE escalations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  negotiation_id UUID REFERENCES negotiations(id) ON DELETE CASCADE,
  escalation_reason VARCHAR(50) NOT NULL,
  severity VARCHAR(20) DEFAULT 'medium',
  status VARCHAR(20) DEFAULT 'pending',
  assigned_to UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_escalations_negotiation_id ON escalations(negotiation_id);
CREATE INDEX idx_escalations_status ON escalations(status);

-- Simulated partners (Module 25)
CREATE TABLE simulated_partners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  business_type VARCHAR(50),
  location GEOMETRY(Point, 4326),
  communication_channel VARCHAR(20) NOT NULL,
  channel_identifier TEXT NOT NULL,
  trust_score INTEGER DEFAULT 80,
  reliability_metrics JSONB,
  business_hours JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_simulated_partners_name ON simulated_partners(name);
CREATE INDEX idx_simulated_partners_location ON simulated_partners USING GIST(location);
CREATE INDEX idx_simulated_partners_is_active ON simulated_partners(is_active);

-- Simulated products
CREATE TABLE simulated_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulated_partner_id UUID REFERENCES simulated_partners(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  inventory_count INTEGER,
  availability_rule VARCHAR(50) DEFAULT 'always',
  availability_conditions JSONB,
  images JSONB,
  capabilities JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_simulated_products_partner_id ON simulated_products(simulated_partner_id);

-- Simulated responses
CREATE TABLE simulated_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulated_partner_id UUID REFERENCES simulated_partners(id) ON DELETE CASCADE,
  scenario_type VARCHAR(50) NOT NULL,
  trigger_conditions JSONB NOT NULL,
  response_template TEXT NOT NULL,
  response_type VARCHAR(20) DEFAULT 'automated',
  response_delay_seconds INTEGER DEFAULT 0,
  randomization JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_simulated_responses_partner_id ON simulated_responses(simulated_partner_id);
CREATE INDEX idx_simulated_responses_scenario_type ON simulated_responses(scenario_type);

-- Simulation logs
CREATE TABLE simulation_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  simulated_partner_id UUID REFERENCES simulated_partners(id) ON DELETE CASCADE,
  request_type VARCHAR(50) NOT NULL,
  request_data JSONB,
  response_data JSONB,
  response_time_ms INTEGER,
  scenario_triggered VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_simulation_logs_partner_id ON simulation_logs(simulated_partner_id);
CREATE INDEX idx_simulation_logs_created_at ON simulation_logs(created_at DESC);

-- Webhook deliveries
CREATE TABLE webhook_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform VARCHAR(50) NOT NULL,
  thread_id VARCHAR(255) NOT NULL,
  payload JSONB NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  delivered_at TIMESTAMPTZ,
  retry_count INTEGER DEFAULT 0,
  failure_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webhook_deliveries_platform_thread ON webhook_deliveries(platform, thread_id);
CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status);

-- Chat thread mappings
CREATE TABLE chat_thread_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  platform VARCHAR(50) NOT NULL,
  thread_id VARCHAR(255) NOT NULL,
  platform_user_id VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(platform, thread_id)
);

CREATE INDEX idx_chat_thread_mappings_user_id ON chat_thread_mappings(user_id);
CREATE INDEX idx_chat_thread_mappings_platform_thread ON chat_thread_mappings(platform, thread_id);

-- Account links
CREATE TABLE account_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  platform VARCHAR(50) NOT NULL,
  platform_user_id VARCHAR(255) NOT NULL,
  oauth_token_hash TEXT,
  permissions JSONB,
  expires_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, platform, platform_user_id)
);

CREATE INDEX idx_account_links_user_id ON account_links(user_id);
CREATE INDEX idx_account_links_platform ON account_links(platform);

COMMIT;
