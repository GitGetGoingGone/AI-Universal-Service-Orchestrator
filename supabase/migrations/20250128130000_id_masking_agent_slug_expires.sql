-- ID masking TTL and agent_slug: Gateway (Orchestrator) stores uso_{agent_slug}_{short_id}; resolve at checkout.
-- Discovery resolves masked_id to internal_product_id; expired rows are ignored.

BEGIN;

ALTER TABLE id_masking_map
  ADD COLUMN IF NOT EXISTS agent_slug TEXT,
  ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_id_masking_map_expires_at ON id_masking_map(expires_at)
  WHERE expires_at IS NOT NULL;

COMMENT ON COLUMN id_masking_map.agent_slug IS 'Business agent slug (e.g. discovery) when masking is done at Gateway.';
COMMENT ON COLUMN id_masking_map.expires_at IS 'TTL: mapping valid until this time; NULL = no expiry.';

COMMIT;
