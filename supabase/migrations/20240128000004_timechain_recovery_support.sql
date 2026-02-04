-- Migration: Time-Chain, Autonomous Recovery, Support Hub, Status (Modules 5, 6, 12, 14)
-- Date: 2024-01-28
-- Dependencies: orders_and_payments

BEGIN;

-- Time-chains (Module 5)
CREATE TABLE time_chains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES bundles(id) ON DELETE CASCADE,
  total_duration_minutes INTEGER NOT NULL,
  calculated_at TIMESTAMPTZ DEFAULT NOW(),
  deadline TIMESTAMPTZ,
  is_feasible BOOLEAN NOT NULL,
  confidence_score DECIMAL(3,2),
  calculation_data JSONB
);

CREATE INDEX idx_time_chains_bundle_id ON time_chains(bundle_id);
CREATE INDEX idx_time_chains_deadline ON time_chains(deadline);

-- Time-chain legs (PostGIS POINT for locations)
CREATE TABLE time_chain_legs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  time_chain_id UUID REFERENCES time_chains(id) ON DELETE CASCADE,
  leg_sequence INTEGER NOT NULL,
  leg_type VARCHAR(50) NOT NULL,
  start_location GEOMETRY(Point, 4326),
  end_location GEOMETRY(Point, 4326),
  estimated_duration_minutes INTEGER NOT NULL,
  actual_duration_minutes INTEGER,
  deadline TIMESTAMPTZ,
  status VARCHAR(20) DEFAULT 'pending',
  partner_id UUID REFERENCES partners(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_time_chain_legs_time_chain_id ON time_chain_legs(time_chain_id);
CREATE INDEX idx_time_chain_legs_status ON time_chain_legs(status);
CREATE INDEX idx_time_chain_legs_locations ON time_chain_legs USING GIST(start_location);
CREATE INDEX idx_time_chain_legs_end_locations ON time_chain_legs USING GIST(end_location);

-- Routes
CREATE TABLE routes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  time_chain_leg_id UUID REFERENCES time_chain_legs(id) ON DELETE CASCADE,
  route_geometry GEOMETRY(LineString, 4326),
  distance_meters DECIMAL(10,2),
  estimated_duration_seconds INTEGER,
  traffic_factor DECIMAL(3,2) DEFAULT 1.0,
  calculated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_routes_leg_id ON routes(time_chain_leg_id);
CREATE INDEX idx_routes_geometry ON routes USING GIST(route_geometry);

-- Conflict analyses
CREATE TABLE conflict_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  new_item_id UUID REFERENCES products(id),
  has_conflict BOOLEAN NOT NULL,
  time_impact_minutes INTEGER,
  conflicts JSONB,
  suggestions JSONB,
  analysis_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conflict_analyses_order_id ON conflict_analyses(order_id);
CREATE INDEX idx_conflict_analyses_has_conflict ON conflict_analyses(has_conflict);

-- Autonomous recoveries (Module 6)
CREATE TABLE autonomous_recoveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  original_leg_id UUID REFERENCES order_legs(id),
  change_request JSONB NOT NULL,
  partner_rejection JSONB NOT NULL,
  recovery_action VARCHAR(50) NOT NULL,
  alternative_item_id UUID REFERENCES products(id),
  alternative_vendor_id UUID REFERENCES partners(id),
  timeline_changed BOOLEAN DEFAULT FALSE,
  delay_minutes INTEGER,
  new_timeline JSONB,
  status VARCHAR(20) DEFAULT 'pending',
  user_approved_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_autonomous_recoveries_order_id ON autonomous_recoveries(order_id);
CREATE INDEX idx_autonomous_recoveries_status ON autonomous_recoveries(status);

-- Recovery attempts
CREATE TABLE recovery_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recovery_id UUID REFERENCES autonomous_recoveries(id) ON DELETE CASCADE,
  attempt_number INTEGER NOT NULL,
  search_criteria JSONB,
  alternatives_found INTEGER DEFAULT 0,
  best_alternative_id UUID REFERENCES products(id),
  search_duration_seconds INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recovery_attempts_recovery_id ON recovery_attempts(recovery_id);

-- Alternative searches
CREATE TABLE alternative_searches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recovery_id UUID REFERENCES autonomous_recoveries(id) ON DELETE CASCADE,
  search_query TEXT NOT NULL,
  results_count INTEGER,
  search_duration_seconds INTEGER,
  filters_applied JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alternative_searches_recovery_id ON alternative_searches(recovery_id);

-- Partner capabilities (Module 9)
CREATE TABLE partner_capabilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID REFERENCES partners(id) ON DELETE CASCADE,
  capability_tag_id UUID REFERENCES capability_tags(id) ON DELETE CASCADE,
  service_area GEOMETRY(Polygon, 4326),
  capacity_limit INTEGER,
  current_capacity INTEGER DEFAULT 0,
  pricing_structure JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(partner_id, capability_tag_id)
);

CREATE INDEX idx_partner_capabilities_partner ON partner_capabilities(partner_id);
CREATE INDEX idx_partner_capabilities_tag ON partner_capabilities(capability_tag_id);
CREATE INDEX idx_partner_capabilities_service_area ON partner_capabilities USING GIST(service_area);

-- Capacity tracking
CREATE TABLE capacity_tracking (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_capability_id UUID REFERENCES partner_capabilities(id) ON DELETE CASCADE,
  current_load INTEGER NOT NULL,
  max_capacity INTEGER NOT NULL,
  utilization_percentage DECIMAL(5,2),
  tracked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_capacity_tracking_partner_capability ON capacity_tracking(partner_capability_id);

-- Conversations (Module 12)
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bundle_id UUID REFERENCES bundles(id) ON DELETE CASCADE,
  order_id UUID REFERENCES orders(id),
  title TEXT,
  status VARCHAR(20) DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_conversations_bundle_id ON conversations(bundle_id);
CREATE INDEX idx_conversations_order_id ON conversations(order_id);
CREATE INDEX idx_conversations_status ON conversations(status);

-- Messages
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  sender_id UUID REFERENCES users(id),
  sender_type VARCHAR(20) NOT NULL,
  sender_name TEXT,
  content TEXT NOT NULL,
  message_type VARCHAR(20) DEFAULT 'text',
  channel VARCHAR(20) NOT NULL,
  channel_message_id TEXT,
  attachments JSONB,
  status VARCHAR(20) DEFAULT 'sent',
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  delivered_at TIMESTAMPTZ,
  read_at TIMESTAMPTZ
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_sent_at ON messages(sent_at DESC);

-- Participants
CREATE TABLE participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  participant_type VARCHAR(20) NOT NULL,
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  last_read_at TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  UNIQUE(conversation_id, user_id)
);

CREATE INDEX idx_participants_conversation_id ON participants(conversation_id);
CREATE INDEX idx_participants_user_id ON participants(user_id);

-- Message attachments
CREATE TABLE message_attachments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  file_type VARCHAR(50),
  file_size_bytes INTEGER,
  storage_url TEXT NOT NULL,
  storage_provider VARCHAR(20) DEFAULT 'azure_blob',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_message_attachments_message_id ON message_attachments(message_id);

-- Status updates (Module 14)
CREATE TABLE status_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  bundle_id UUID REFERENCES bundles(id),
  status_type VARCHAR(50) NOT NULL,
  previous_status VARCHAR(50),
  new_status VARCHAR(50) NOT NULL,
  narrative TEXT NOT NULL,
  agent_reasoning TEXT,
  adaptive_card JSONB,
  sent_via JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_status_updates_order_id ON status_updates(order_id);
CREATE INDEX idx_status_updates_created_at ON status_updates(created_at DESC);

-- Progress ledgers
CREATE TABLE progress_ledgers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  standing_intent_id UUID,
  order_id UUID REFERENCES orders(id),
  step_number INTEGER NOT NULL,
  step_name TEXT NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  thought TEXT,
  narrative TEXT,
  if_then_logic JSONB,
  adaptive_card JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX idx_progress_ledgers_order_id ON progress_ledgers(order_id);
CREATE INDEX idx_progress_ledgers_status ON progress_ledgers(status);

-- Agent reasoning logs
CREATE TABLE agent_reasoning_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status_update_id UUID REFERENCES status_updates(id),
  reasoning_context JSONB NOT NULL,
  extracted_reasoning TEXT,
  confidence_score DECIMAL(3,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_reasoning_logs_status_update ON agent_reasoning_logs(status_update_id);

COMMIT;
