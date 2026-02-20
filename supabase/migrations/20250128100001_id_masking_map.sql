-- ID masking: masked_id (returned to clients) -> internal product_id for checkout/fulfillment.
-- Gateway maintains this mapping; client never sees internal ids.

BEGIN;

CREATE TABLE IF NOT EXISTS id_masking_map (
  masked_id TEXT PRIMARY KEY,
  internal_product_id TEXT NOT NULL,
  partner_id TEXT,
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_id_masking_map_internal ON id_masking_map(internal_product_id);

COMMENT ON TABLE id_masking_map IS 'USO Gateway: masked product ids returned to clients -> internal id for add-to-bundle/checkout.';

COMMIT;
