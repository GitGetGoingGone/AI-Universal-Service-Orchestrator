-- Semantic enrichment: knowledge-base-style text for product embeddings (e.g. "best used for", use cases, FAQs).
-- Included in embedding input in discovery-service semantic_search for better semantic search.
ALTER TABLE products
  ADD COLUMN IF NOT EXISTS description_kb TEXT;

COMMENT ON COLUMN products.description_kb IS 'Optional long-form or structured text for semantic search (use cases, best for, FAQs). Included in product embedding.';
