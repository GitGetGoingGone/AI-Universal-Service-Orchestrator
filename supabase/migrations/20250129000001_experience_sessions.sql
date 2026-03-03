-- Experience Sessions and Legs: track session state for WhatsApp/SMS resume.
-- Leg status: pending, ready, in_customization, committed.

BEGIN;

CREATE TABLE IF NOT EXISTS experience_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id TEXT NOT NULL,
  user_id UUID REFERENCES users(id),
  status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experience_sessions_thread ON experience_sessions(thread_id);
CREATE INDEX IF NOT EXISTS idx_experience_sessions_user ON experience_sessions(user_id);

COMMENT ON TABLE experience_sessions IS 'Experience session for bundle; linked to thread_id for WhatsApp/SMS resume.';

CREATE TABLE IF NOT EXISTS experience_session_legs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experience_session_id UUID REFERENCES experience_sessions(id) ON DELETE CASCADE,
  partner_id UUID REFERENCES partners(id),
  product_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  shopify_draft_order_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experience_session_legs_session ON experience_session_legs(experience_session_id);
CREATE INDEX IF NOT EXISTS idx_experience_session_legs_status ON experience_session_legs(status);

COMMENT ON TABLE experience_session_legs IS 'Leg per partner/product: pending, ready, in_customization, committed.';
COMMENT ON COLUMN experience_session_legs.product_id IS 'Masked product id (uso_*).';

CREATE TABLE IF NOT EXISTS experience_session_leg_overrides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  leg_id UUID REFERENCES experience_session_legs(id) ON DELETE CASCADE,
  admin_id UUID NOT NULL,
  old_status TEXT NOT NULL,
  new_status TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experience_session_leg_overrides_leg ON experience_session_leg_overrides(leg_id);

COMMENT ON TABLE experience_session_leg_overrides IS 'Audit trail for admin manual status overrides.';

COMMIT;
