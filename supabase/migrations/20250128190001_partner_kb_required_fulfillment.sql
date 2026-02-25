-- Partner KB articles can declare required fulfillment fields (e.g. custom letter needs theme_for_message, customization needs custom_text).
-- When discovery returns kb_articles with include_kb_articles=true, orchestrator merges these into required_fulfillment_fields for the checkout gate.

BEGIN;

ALTER TABLE partner_kb_articles
  ADD COLUMN IF NOT EXISTS required_fulfillment_fields JSONB;

COMMENT ON COLUMN partner_kb_articles.required_fulfillment_fields IS 'Optional array of fulfillment field keys this article requires (e.g. ["theme_for_message","custom_text"]). Merged with admin default and bundle fields before checkout.';

COMMIT;
