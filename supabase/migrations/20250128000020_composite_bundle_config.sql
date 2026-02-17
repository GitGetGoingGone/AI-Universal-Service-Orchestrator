-- Migration: suggest_composite_bundle prompt + composite_discovery_config
-- Dependencies: model_interaction_prompts, platform_config

BEGIN;

-- Add suggest_composite_bundle to model_interaction_prompts (admin-editable bundle curation)
INSERT INTO model_interaction_prompts (interaction_type, display_name, when_used, system_prompt, enabled, max_tokens, display_order)
VALUES (
  'suggest_composite_bundle',
  'Bundle Curation (Composite)',
  'When discover_composite returns products. LLM suggests 2-4 bundle options (one product per category per option).',
  'You are a bundle curator. Given categories with products for a composite experience, suggest 2-4 different options. Each option: one product per category. Return JSON: { options: [{ label, description, product_ids, total_price }] }. ONLY use product IDs from the list. Consider: theme fit, budget, diversity between options.',
  true, 500, 8
)
ON CONFLICT (interaction_type) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  when_used = EXCLUDED.when_used,
  system_prompt = EXCLUDED.system_prompt,
  max_tokens = EXCLUDED.max_tokens,
  display_order = EXCLUDED.display_order;

-- Add composite_discovery_config to platform_config
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS composite_discovery_config JSONB DEFAULT '{
  "products_per_category": 5,
  "sponsorship_enabled": true,
  "product_mix": [
    {"sort": "price_desc", "limit": 10, "pct": 50},
    {"sort": "price_asc", "limit": 10, "pct": 20},
    {"sort": "rating", "limit": 10, "pct": 10},
    {"sort": "popularity", "limit": 10, "pct": 10},
    {"sort": "sponsored", "limit": 10, "pct": 10}
  ]
}'::jsonb;

COMMENT ON COLUMN platform_config.composite_discovery_config IS 'Composite discovery: products_per_category, product_mix (sort slices with pct), sponsorship_enabled';

-- Enable/disable LLM bundle suggestion for composite experiences
ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS enable_composite_bundle_suggestion BOOLEAN DEFAULT true;
COMMENT ON COLUMN platform_config.enable_composite_bundle_suggestion IS 'When true, LLM suggests 2-4 bundle options after discover_composite. When false, products only.';

COMMIT;
