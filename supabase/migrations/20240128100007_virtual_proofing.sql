-- Migration: Virtual Proofing Engine (Module 8)
-- Proof state machine, approval workflow
-- Dependencies: orders_and_payments

BEGIN;

CREATE TABLE proof_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
  order_leg_id UUID REFERENCES order_legs(id) ON DELETE SET NULL,
  proof_type VARCHAR(50) NOT NULL DEFAULT 'virtual_preview',
  current_state VARCHAR(50) NOT NULL DEFAULT 'pending',
  proof_image_url TEXT,
  prompt_used TEXT,
  proof_metadata JSONB DEFAULT '{}',
  submitted_by UUID REFERENCES users(id),
  approved_by UUID REFERENCES users(id),
  approval_method VARCHAR(50),
  approval_confidence DECIMAL(5,2),
  rejection_reason TEXT,
  submitted_at TIMESTAMPTZ,
  approved_at TIMESTAMPTZ,
  time_chain_paused BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_proof_states_order_id ON proof_states(order_id);
CREATE INDEX idx_proof_states_current_state ON proof_states(current_state);

CREATE TABLE proof_state_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proof_state_id UUID NOT NULL REFERENCES proof_states(id) ON DELETE CASCADE,
  from_state VARCHAR(50),
  to_state VARCHAR(50),
  transitioned_by UUID REFERENCES users(id),
  transition_reason TEXT,
  transitioned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_proof_transitions_proof_state ON proof_state_transitions(proof_state_id);

COMMENT ON TABLE proof_states IS 'Module 8: Proof state for virtual proofing workflow';
COMMENT ON TABLE proof_state_transitions IS 'Module 8: Proof state transition log';

COMMIT;
