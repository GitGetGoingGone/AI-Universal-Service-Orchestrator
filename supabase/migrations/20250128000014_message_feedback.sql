-- Migration: Message feedback for analytics and personalization
-- Stores Like/Dislike on product suggestions for ranking and personalization

BEGIN;

CREATE TABLE IF NOT EXISTS message_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id UUID NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
  message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
  rating VARCHAR(10) NOT NULL CHECK (rating IN ('like', 'dislike')),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  anonymous_id TEXT,
  context JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_message_feedback_thread_id ON message_feedback(thread_id);
CREATE INDEX idx_message_feedback_rating ON message_feedback(rating);
CREATE INDEX idx_message_feedback_user_id ON message_feedback(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_message_feedback_anonymous_id ON message_feedback(anonymous_id) WHERE anonymous_id IS NOT NULL;
CREATE INDEX idx_message_feedback_created_at ON message_feedback(created_at DESC);

COMMENT ON TABLE message_feedback IS 'User feedback (like/dislike) on assistant messages for analytics and personalization';

COMMIT;
