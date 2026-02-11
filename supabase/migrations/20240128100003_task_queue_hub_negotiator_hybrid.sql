-- Migration: Multi-Vendor Task Queue (Module 11), HubNegotiator & Bidding (Module 10), Hybrid Response Logic (Module 13)
-- Dependencies: orders_and_payments, omnichannel_simulator_supporting

BEGIN;

-- ========== Module 11: Multi-Vendor Task Queue ==========
-- One task per order_leg; partners see and complete tasks in sequence.
CREATE TABLE vendor_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  order_leg_id UUID NOT NULL REFERENCES order_legs(id) ON DELETE CASCADE,
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  task_sequence INTEGER NOT NULL,
  task_type VARCHAR(50) NOT NULL DEFAULT 'fulfill',
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  metadata JSONB,
  UNIQUE(order_id, order_leg_id)
);

CREATE INDEX idx_vendor_tasks_partner_id ON vendor_tasks(partner_id);
CREATE INDEX idx_vendor_tasks_order_id ON vendor_tasks(order_id);
CREATE INDEX idx_vendor_tasks_status ON vendor_tasks(status);
CREATE INDEX idx_vendor_tasks_partner_status ON vendor_tasks(partner_id, status);

COMMENT ON TABLE vendor_tasks IS 'Module 11: Task queue for multi-vendor orders; one task per order_leg, ordered by task_sequence';

-- ========== Module 10: HubNegotiator & Bidding ==========
-- RFPs (requests for proposal) for assembly/delivery; hubs submit bids; winner gets task.
CREATE TABLE rfps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  bundle_id UUID REFERENCES bundles(id) ON DELETE CASCADE,
  request_type VARCHAR(50) NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  delivery_address JSONB,
  deadline TIMESTAMPTZ NOT NULL,
  compensation_cents INTEGER,
  status VARCHAR(20) NOT NULL DEFAULT 'open',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  closed_at TIMESTAMPTZ,
  metadata JSONB
);

CREATE INDEX idx_rfps_status ON rfps(status);
CREATE INDEX idx_rfps_deadline ON rfps(deadline);
CREATE INDEX idx_rfps_order_id ON rfps(order_id);

CREATE TABLE bids (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rfp_id UUID NOT NULL REFERENCES rfps(id) ON DELETE CASCADE,
  hub_partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  amount_cents INTEGER NOT NULL,
  proposed_completion_at TIMESTAMPTZ,
  status VARCHAR(20) NOT NULL DEFAULT 'submitted',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB,
  UNIQUE(rfp_id, hub_partner_id)
);

CREATE INDEX idx_bids_rfp_id ON bids(rfp_id);
CREATE INDEX idx_bids_hub_partner_id ON bids(hub_partner_id);

CREATE TABLE hub_capacity (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  capacity_slots INTEGER NOT NULL DEFAULT 1,
  available_from TIMESTAMPTZ NOT NULL,
  available_until TIMESTAMPTZ NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hub_capacity_partner_id ON hub_capacity(partner_id);
CREATE INDEX idx_hub_capacity_available ON hub_capacity(available_from, available_until);

ALTER TABLE rfps ADD COLUMN winning_bid_id UUID REFERENCES bids(id);
CREATE INDEX idx_rfps_winning_bid ON rfps(winning_bid_id);

COMMENT ON TABLE rfps IS 'Module 10: Request for proposal (assembly/delivery); hubs bid via bids table';
COMMENT ON TABLE bids IS 'Module 10: Hub bids on RFPs';
COMMENT ON TABLE hub_capacity IS 'Module 10: Hub capacity windows for capacity matching';

-- ========== Module 13: Hybrid Response Logic ==========
-- Classify incoming messages; route to AI or human (escalation).
CREATE TABLE support_escalations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_ref VARCHAR(255) NOT NULL,
  classification VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  assigned_to UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  resolution_notes TEXT
);

CREATE TABLE response_classifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_ref VARCHAR(255) NOT NULL,
  message_content TEXT NOT NULL,
  classification VARCHAR(50) NOT NULL,
  route VARCHAR(20) NOT NULL,
  support_escalation_id UUID REFERENCES support_escalations(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_response_classifications_conversation ON response_classifications(conversation_ref);
CREATE INDEX idx_support_escalations_status ON support_escalations(status);
CREATE INDEX idx_support_escalations_assigned ON support_escalations(assigned_to);

COMMENT ON TABLE response_classifications IS 'Module 13: Log of AI vs human routing decisions';
COMMENT ON TABLE support_escalations IS 'Module 13: Human-handled escalations from hybrid response';

COMMIT;
