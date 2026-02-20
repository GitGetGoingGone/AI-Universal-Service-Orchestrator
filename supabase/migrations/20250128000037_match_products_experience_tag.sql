-- Migration: Add optional filter_experience_tag to match_products for experience-tag-based discovery
-- When set, only products whose experience_tags JSONB contains the tag are returned.

BEGIN;

CREATE OR REPLACE FUNCTION match_products(
  query_embedding vector(1536),
  match_count int DEFAULT 20,
  match_threshold float DEFAULT 0.5,
  filter_partner_id uuid DEFAULT NULL,
  exclude_partner_id uuid DEFAULT NULL,
  filter_experience_tag text DEFAULT NULL
)
RETURNS SETOF products
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT p.*
  FROM products p
  WHERE p.deleted_at IS NULL
    AND p.embedding IS NOT NULL
    AND (1 - (p.embedding <=> query_embedding)) > match_threshold
    AND (filter_partner_id IS NULL OR p.partner_id = filter_partner_id)
    AND (exclude_partner_id IS NULL OR p.partner_id != exclude_partner_id)
    AND (filter_experience_tag IS NULL OR p.experience_tags ? filter_experience_tag)
  ORDER BY p.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_products(vector(1536), int, float, uuid, uuid, text) IS 'Module 1: Semantic product search via pgvector; optional filter_experience_tag for experience-tag containment';

COMMIT;
