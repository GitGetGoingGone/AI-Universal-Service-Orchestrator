-- Commitment-First Orchestration: schema extensions for vendor-agnostic commitment,
-- modification window, supplemental charges, SLA re-sourcing, and hybrid customization.
-- Dependencies: experience_sessions, orders_and_payments, hybrid_registry_shopify

BEGIN;

-- experience_sessions: intent_summary for headless context; optional customization_partner_id; order_id for SLA
ALTER TABLE experience_sessions
  ADD COLUMN IF NOT EXISTS intent_summary TEXT,
  ADD COLUMN IF NOT EXISTS customization_partner_id UUID REFERENCES partners(id),
  ADD COLUMN IF NOT EXISTS order_id UUID REFERENCES orders(id);

CREATE INDEX IF NOT EXISTS idx_experience_sessions_order
  ON experience_sessions(order_id)
  WHERE order_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_experience_sessions_customization_partner
  ON experience_sessions(customization_partner_id)
  WHERE customization_partner_id IS NOT NULL;

COMMENT ON COLUMN experience_sessions.intent_summary IS 'Short narrative for design chat headless context (e.g. Experience: Date Night; User asked for romantic dinner + flowers).';
COMMENT ON COLUMN experience_sessions.customization_partner_id IS 'Optional partner for design/customization when different from selling partner (hybrid customization).';

-- experience_session_legs: vendor-agnostic external refs, modification window, SLA
ALTER TABLE experience_session_legs
  ADD COLUMN IF NOT EXISTS external_order_id TEXT,
  ADD COLUMN IF NOT EXISTS external_reservation_id TEXT,
  ADD COLUMN IF NOT EXISTS vendor_type VARCHAR(20) DEFAULT 'local',
  ADD COLUMN IF NOT EXISTS allows_modification BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS design_started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS re_sourcing_state TEXT,
  ADD COLUMN IF NOT EXISTS customization_partner_id UUID REFERENCES partners(id);

CREATE INDEX IF NOT EXISTS idx_experience_session_legs_vendor_type
  ON experience_session_legs(vendor_type);
CREATE INDEX IF NOT EXISTS idx_experience_session_legs_re_sourcing_state
  ON experience_session_legs(re_sourcing_state)
  WHERE re_sourcing_state IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_experience_session_legs_design_started
  ON experience_session_legs(design_started_at)
  WHERE design_started_at IS NULL;

COMMENT ON COLUMN experience_session_legs.external_order_id IS 'Vendor order reference (e.g. Shopify order id when vendor_type=shopify).';
COMMENT ON COLUMN experience_session_legs.external_reservation_id IS 'Vendor reservation/draft id before complete (e.g. Shopify draft_order_id).';
COMMENT ON COLUMN experience_session_legs.vendor_type IS 'shopify, ucp, local - selects commitment provider.';
COMMENT ON COLUMN experience_session_legs.allows_modification IS 'False when partner started design (Point of No Return); Replace/Delete blocked.';
COMMENT ON COLUMN experience_session_legs.design_started_at IS 'When partner actually started design chat.';
COMMENT ON COLUMN experience_session_legs.re_sourcing_state IS 'awaiting_user_response when SLA exceeded and user notified; stores pending switch state.';
COMMENT ON COLUMN experience_session_legs.customization_partner_id IS 'Partner for design when different from selling partner (per-leg override).';

-- order_legs: vendor-agnostic external refs for re-sourcing
ALTER TABLE order_legs
  ADD COLUMN IF NOT EXISTS external_order_id TEXT,
  ADD COLUMN IF NOT EXISTS external_reservation_id TEXT,
  ADD COLUMN IF NOT EXISTS vendor_type VARCHAR(20) DEFAULT 'local';

COMMENT ON COLUMN order_legs.external_order_id IS 'Vendor order reference for cancel/refund.';
COMMENT ON COLUMN order_legs.external_reservation_id IS 'Vendor reservation id before complete.';
COMMENT ON COLUMN order_legs.vendor_type IS 'shopify, ucp, local.';

-- internal_agent_registry: SLA and design chat endpoint
ALTER TABLE internal_agent_registry
  ADD COLUMN IF NOT EXISTS sla_response_hours NUMERIC(5,2) DEFAULT 24,
  ADD COLUMN IF NOT EXISTS design_chat_url TEXT,
  ADD COLUMN IF NOT EXISTS commitment_vendor_type VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_internal_agent_registry_commitment_vendor
  ON internal_agent_registry(commitment_vendor_type)
  WHERE commitment_vendor_type IS NOT NULL;

COMMENT ON COLUMN internal_agent_registry.sla_response_hours IS 'Hours to wait for partner design start before notifying user for re-sourcing.';
COMMENT ON COLUMN internal_agent_registry.design_chat_url IS 'Partner design chat endpoint for startDesignChat proxy.';
COMMENT ON COLUMN internal_agent_registry.commitment_vendor_type IS 'shopify, ucp, local - overrides transport_type for commitment provider selection.';

-- shopify_curated_partners: design_chat_url override (optional)
ALTER TABLE shopify_curated_partners
  ADD COLUMN IF NOT EXISTS design_chat_url TEXT;

COMMENT ON COLUMN shopify_curated_partners.design_chat_url IS 'Override design chat endpoint for this Shopify partner.';

-- payments: experience_session link and payment_type for supplemental charges
ALTER TABLE payments
  ADD COLUMN IF NOT EXISTS experience_session_id UUID REFERENCES experience_sessions(id),
  ADD COLUMN IF NOT EXISTS payment_type VARCHAR(20) DEFAULT 'initial';

CREATE INDEX IF NOT EXISTS idx_payments_experience_session
  ON payments(experience_session_id)
  WHERE experience_session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payments_payment_type
  ON payments(payment_type);

COMMENT ON COLUMN payments.experience_session_id IS 'Links supplemental charges to experience session.';
COMMENT ON COLUMN payments.payment_type IS 'initial or supplemental.';

-- sla_re_sourcing_pending: store alternatives when awaiting user response
CREATE TABLE IF NOT EXISTS sla_re_sourcing_pending (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experience_session_leg_id UUID REFERENCES experience_session_legs(id) ON DELETE CASCADE,
  alternatives_snapshot JSONB NOT NULL DEFAULT '[]',
  notified_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sla_re_sourcing_pending_leg
  ON sla_re_sourcing_pending(experience_session_leg_id);

COMMENT ON TABLE sla_re_sourcing_pending IS 'Stores similar alternatives when SLA exceeded; used when user confirms switch.';

COMMIT;
