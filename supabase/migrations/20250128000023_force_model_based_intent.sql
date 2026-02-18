-- Force model-based intent for ChatGPT/Gemini (no heuristic fallback)
-- When true and platform is chatgpt/gemini, intent service uses LLM only; fails if LLM unavailable.

ALTER TABLE platform_config ADD COLUMN IF NOT EXISTS force_model_based_intent BOOLEAN DEFAULT false;
COMMENT ON COLUMN platform_config.force_model_based_intent IS 'When true and platform is chatgpt/gemini, use LLM for intent only; do not fall back to heuristics. Ensures probing data (date, budget, preferences) are captured by model.';
