-- Add fulfillment_details to bundles for composite experiences (pickup time, pickup address, delivery address)
-- Required before add_bundle_bulk for date night and similar experiences

ALTER TABLE bundles
ADD COLUMN IF NOT EXISTS fulfillment_details JSONB DEFAULT NULL;

COMMENT ON COLUMN bundles.fulfillment_details IS 'Pickup time, pickup address, delivery address for composite experiences (date night, etc.)';
