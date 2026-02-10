-- Migration: Scout Engine semantic search (Module 1)
-- Date: 2024-01-28
-- Adds RPC for pgvector similarity search on products

BEGIN;

-- RPC: Match products by embedding similarity (cosine distance)
-- Called via Supabase client: .rpc('match_products', {...})
CREATE OR REPLACE FUNCTION match_products(
  query_embedding vector(1536),
  match_count int DEFAULT 20,
  match_threshold float DEFAULT 0.5,
  filter_partner_id uuid DEFAULT NULL,
  exclude_partner_id uuid DEFAULT NULL
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
  ORDER BY p.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_products IS 'Module 1: Semantic product search via pgvector cosine similarity';

COMMIT;
