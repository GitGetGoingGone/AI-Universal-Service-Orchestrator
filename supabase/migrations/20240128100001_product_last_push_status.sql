-- Per-product ACP push status for portal display (last pushed at, success).
-- Reference: docs/AI_PLATFORM_PRODUCT_DISCOVERY.md

BEGIN;

ALTER TABLE products ADD COLUMN IF NOT EXISTS last_acp_push_at TIMESTAMPTZ;
ALTER TABLE products ADD COLUMN IF NOT EXISTS last_acp_push_success BOOLEAN;

COMMENT ON COLUMN products.last_acp_push_at IS 'When this product was last included in an ACP push';
COMMENT ON COLUMN products.last_acp_push_success IS 'Whether the last ACP push for this product succeeded';

COMMIT;
