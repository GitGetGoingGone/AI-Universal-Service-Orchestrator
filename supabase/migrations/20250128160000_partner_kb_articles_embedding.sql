-- Semantic search over partner KB articles (Module 1).
-- Adds embedding column and match_kb_articles RPC for pgvector similarity search.

BEGIN;

-- Add embedding column to partner_kb_articles (1536 dims: text-embedding-3-small / ada-002)
ALTER TABLE partner_kb_articles
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

COMMENT ON COLUMN partner_kb_articles.embedding IS 'Embedding of title+content for semantic KB search (Module 1).';

-- Index for cosine similarity search
CREATE INDEX IF NOT EXISTS idx_partner_kb_articles_embedding
  ON partner_kb_articles USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100)
  WHERE embedding IS NOT NULL;

-- RPC: Match KB articles by embedding similarity (cosine distance)
CREATE OR REPLACE FUNCTION match_kb_articles(
  query_embedding vector(1536),
  match_count int DEFAULT 20,
  match_threshold float DEFAULT 0.0,
  filter_partner_id uuid DEFAULT NULL,
  exclude_partner_id uuid DEFAULT NULL
)
RETURNS SETOF partner_kb_articles
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT a.*
  FROM partner_kb_articles a
  WHERE a.is_active = TRUE
    AND a.embedding IS NOT NULL
    AND (1 - (a.embedding <=> query_embedding)) > match_threshold
    AND (filter_partner_id IS NULL OR a.partner_id = filter_partner_id)
    AND (exclude_partner_id IS NULL OR a.partner_id != exclude_partner_id)
  ORDER BY a.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION match_kb_articles(vector(1536), int, float, uuid, uuid) IS 'Module 1: Semantic search over partner KB articles via pgvector cosine similarity';

COMMIT;
