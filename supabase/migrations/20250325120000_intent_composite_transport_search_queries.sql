-- Ensure composite intent includes transport (and each leg) in search_queries when relevant.
-- Appends to intent system_prompt; safe if section already present (duplicate is harmless for ops).

BEGIN;

UPDATE model_interaction_prompts
SET
  system_prompt = system_prompt || E'\n\n=== MULTI-LEG COMPOSITE (SEARCH QUERIES) ===\nFor discover_composite, search_queries must list one distinct entry per capability leg the user wants (use the same short category tokens you use elsewhere—e.g. retail goods, dining, transport). When the user expects coordinated logistics across stops and has not removed that leg, include a transport-capability token in search_queries so discovery can return catalog rows. Keep proposed_plan consistent with search_queries—do not promise a leg in the itinerary that you excluded from search_queries.',

  updated_at = NOW()
WHERE interaction_type = 'intent';

COMMIT;
