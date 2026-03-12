-- Migration: intent_heuristic_config on platform_config (admin-configurable intent heuristics)
-- Used by intent-service heuristic fallback: probe keywords, composite patterns, discover keywords, etc.

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS intent_heuristic_config JSONB DEFAULT '{
  "probe_keywords": ["budget", "dietary", "preferences", "location", "what date", "occasion", "add flowers", "add something", "?"],
  "unrelated_phrases": ["show more options", "more options", "other options", "different options", "you suggest", "suggest", "whatever", "anything"],
  "composite_patterns": [
    {"pattern": "date\\s*night|plan\\s*a\\s*date|romantic\\s*evening", "search_queries": ["flowers", "dinner", "limo"], "experience_name": "date night", "proposed_plan": ["Flowers", "Dinner", "Limo"]},
    {"pattern": "birthday\\s*party|birthday\\s*celebration", "search_queries": ["cake", "flowers", "gifts"], "experience_name": "birthday party", "proposed_plan": ["Cake", "Flowers", "Gifts"]},
    {"pattern": "picnic", "search_queries": ["basket", "blanket", "food"], "experience_name": "picnic", "proposed_plan": ["Basket", "Blanket", "Food"]},
    {"pattern": "baby\\s*shower", "search_queries": ["cake", "decorations", "gifts"], "experience_name": "baby shower", "proposed_plan": ["Cake", "Decorations", "Gifts"]}
  ],
  "simple_discover_keywords": ["gift", "gifts"],
  "discover_with_probe_keywords": ["gift", "birthday"],
  "location_like_words": ["downtown", "midtown", "uptown", "dallas", "nyc", "brooklyn", "manhattan", "houston", "austin", "chicago", "la", "sf", "seattle", "boston", "miami", "near me", "around me", "here", "local"],
  "remove_patterns": [
    {"pattern": "\\bno\\s+limo\\b|remove\\s+(?:the\\s+)?limo|without\\s+(?:the\\s+)?limo|skip\\s+limo", "category_key": "limo"},
    {"pattern": "\\bno\\s+flowers\\b|remove\\s+(?:the\\s+)?flowers|without\\s+flowers|skip\\s+flowers|don''?t\\s+want\\s+flowers", "category_key": "flowers"},
    {"pattern": "\\bno\\s+dinner\\b|remove\\s+(?:the\\s+)?dinner|without\\s+dinner|skip\\s+dinner", "category_key": "dinner"},
    {"pattern": "\\bno\\s+chocolates\\b|remove\\s+(?:the\\s+)?chocolates|without\\s+chocolates|skip\\s+chocolates", "category_key": "chocolates"},
    {"pattern": "\\bno\\s+cake\\b|remove\\s+(?:the\\s+)?cake|without\\s+cake|skip\\s+cake", "category_key": "cake"},
    {"pattern": "\\bno\\s+movies\\b|remove\\s+(?:the\\s+)?movies|without\\s+movies|skip\\s+movies", "category_key": "movies"},
    {"pattern": "\\bno\\s+gifts\\b|remove\\s+(?:the\\s+)?gifts|without\\s+gifts", "category_key": "gifts"},
    {"pattern": "\\bno\\s+decorations\\b|remove\\s+(?:the\\s+)?decorations|without\\s+decorations", "category_key": "decorations"}
  ],
  "cat_to_label": {"limo": "Limo", "flowers": "Flowers", "dinner": "Dinner", "chocolates": "Chocolates", "cake": "Cake", "movies": "Movies", "gifts": "Gifts", "decorations": "Decorations", "basket": "Basket", "blanket": "Blanket", "food": "Food"}
}'::jsonb;

COMMENT ON COLUMN platform_config.intent_heuristic_config IS 'Intent heuristic fallback: probe_keywords, unrelated_phrases, composite_patterns (pattern, search_queries, experience_name, proposed_plan), simple_discover_keywords, discover_with_probe_keywords, location_like_words, remove_patterns (pattern, category_key), cat_to_label. Editable in Platform Config > Discovery > Intent heuristics.';
