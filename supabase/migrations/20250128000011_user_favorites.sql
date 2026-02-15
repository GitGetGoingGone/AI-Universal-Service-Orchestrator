-- Migration: User Favorites for "My Stuff"
-- Stores products/items a user has favorited

BEGIN;

CREATE TABLE IF NOT EXISTS user_favorites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  anonymous_id TEXT,
  item_type VARCHAR(50) NOT NULL DEFAULT 'product',
  item_id TEXT NOT NULL,
  item_name TEXT,
  item_metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT chk_user_or_anonymous CHECK (user_id IS NOT NULL OR anonymous_id IS NOT NULL)
);

CREATE UNIQUE INDEX idx_user_favorites_user_unique ON user_favorites(user_id, item_type, item_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX idx_user_favorites_anon_unique ON user_favorites(anonymous_id, item_type, item_id) WHERE anonymous_id IS NOT NULL;

CREATE INDEX idx_user_favorites_user_id ON user_favorites(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_user_favorites_anonymous_id ON user_favorites(anonymous_id) WHERE anonymous_id IS NOT NULL;
CREATE INDEX idx_user_favorites_created_at ON user_favorites(created_at DESC);

COMMENT ON TABLE user_favorites IS 'User favorites for My Stuff - products and saved items';

COMMIT;
