-- RPC: Return distinct experience tags from products for discovery filters / experience-categories API.

BEGIN;

CREATE OR REPLACE FUNCTION get_distinct_experience_tags()
RETURNS TABLE(tag text)
LANGUAGE sql
STABLE
AS $$
  SELECT DISTINCT jsonb_array_elements_text(p.experience_tags) AS tag
  FROM products p
  WHERE p.deleted_at IS NULL
    AND p.experience_tags IS NOT NULL
    AND jsonb_array_length(p.experience_tags) > 0
  ORDER BY tag;
$$;

COMMENT ON FUNCTION get_distinct_experience_tags IS 'Returns distinct experience_tags values from products for GET /api/v1/experience-categories';

COMMIT;
