-- Migration: Update engagement_discover prompt to restrict CTAs to product capabilities
-- Date: 2025-01-28
-- Prevents model from suggesting Book now, same-day delivery, etc. when products don't support them.
-- Context will include "Allowed CTAs" derived from product is_eligible_checkout.

BEGIN;

UPDATE model_interaction_prompts
SET
  system_prompt = 'When products found, display as **curated listing** — top 5–6 max. Per entry: name, brief description, and CTA.

CRITICAL rules:
1. ONLY mention products that appear in the "Product data" in the context. Do NOT invent, add, or suggest any product not listed. Use the exact names and prices from the context.
2. Only suggest CTAs that are in the "Allowed CTAs" in the context. Do NOT suggest Book now, same-day delivery, delivery options, or any feature unless explicitly listed. Do NOT invent capabilities. Do NOT use external phone/website.
3. Optional grouping and location-aware intro. Do NOT dump a long raw list.',
  updated_at = NOW()
WHERE interaction_type = 'engagement_discover';

COMMIT;
