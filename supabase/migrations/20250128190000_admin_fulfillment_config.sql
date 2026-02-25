-- Configurable fulfillment: admin default required fields and human-readable labels.
-- Partners can override per bundle/KB; this is the platform default (e.g. delivery_address, pickup_address, pickup_time).

BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'admin_orchestration_settings' AND column_name = 'default_fulfillment_fields'
  ) THEN
    ALTER TABLE admin_orchestration_settings ADD COLUMN default_fulfillment_fields JSONB;
    COMMENT ON COLUMN admin_orchestration_settings.default_fulfillment_fields IS 'Default required fulfillment field keys (e.g. ["delivery_address","pickup_address","pickup_time"]). Merged with bundle/KB-specific fields.';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'admin_orchestration_settings' AND column_name = 'default_fulfillment_field_labels'
  ) THEN
    ALTER TABLE admin_orchestration_settings ADD COLUMN default_fulfillment_field_labels JSONB;
    COMMENT ON COLUMN admin_orchestration_settings.default_fulfillment_field_labels IS 'Human-readable labels: {"delivery_address": "delivery address", "theme_for_message": "theme for the message"}.';
  END IF;
END $$;

-- Optional: set default so existing row has standard shipping fields
UPDATE admin_orchestration_settings
SET default_fulfillment_fields = COALESCE(default_fulfillment_fields, '["delivery_address","pickup_address","pickup_time"]'::jsonb),
    default_fulfillment_field_labels = COALESCE(default_fulfillment_field_labels, '{"delivery_address":"delivery address","pickup_address":"pickup address","pickup_time":"pickup time"}'::jsonb)
WHERE default_fulfillment_fields IS NULL OR default_fulfillment_field_labels IS NULL;

COMMIT;
