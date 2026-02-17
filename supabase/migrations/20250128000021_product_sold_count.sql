-- Migration: Add sold_count to products for popularity-based product mix
-- Dependencies: products

BEGIN;

ALTER TABLE products ADD COLUMN IF NOT EXISTS sold_count INT DEFAULT 0;
COMMENT ON COLUMN products.sold_count IS 'Number of times product was sold (for popularity ranking). Updated by order webhook or nightly job.';

COMMIT;
