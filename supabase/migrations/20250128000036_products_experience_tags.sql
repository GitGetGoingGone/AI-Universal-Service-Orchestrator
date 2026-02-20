-- Products: experience/thematic tags for search and recommendations (e.g. luxury, night out, travel, celebration).
-- Distinct from capability_tags (category/capability like limo, flowers). Editable in partner portal product page.

BEGIN;

ALTER TABLE products ADD COLUMN IF NOT EXISTS experience_tags JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN products.experience_tags IS 'Thematic/experience tags for discovery: e.g. ["luxury", "night out", "travel", "celebration"]. Used in search/recommendations; editable in partner portal.';

CREATE INDEX IF NOT EXISTS idx_products_experience_tags ON products USING GIN (experience_tags);

COMMIT;
