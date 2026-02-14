-- Migration: Chat threads for web app conversation persistence (Return Visit UX)
-- Date: 2025-01-28
-- Dependencies: core_and_scout, intent_and_bundle

BEGIN;

CREATE TABLE chat_threads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  anonymous_id TEXT,
  partner_id UUID REFERENCES partners(id),
  title TEXT,
  bundle_id UUID REFERENCES bundles(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id UUID NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL,
  content TEXT,
  adaptive_card JSONB,
  channel VARCHAR(20) DEFAULT 'web',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_threads_user_id ON chat_threads(user_id);
CREATE INDEX idx_chat_threads_anonymous_id ON chat_threads(anonymous_id);
CREATE INDEX idx_chat_threads_partner_id ON chat_threads(partner_id);
CREATE INDEX idx_chat_messages_thread_id ON chat_messages(thread_id);

COMMIT;
