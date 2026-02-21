-- Migration: Persist refinement context (e.g. "no limo" -> flowers + dinner) per thread at service level
-- So the orchestrator can restore it on the next turn without the client sending refinement_context

BEGIN;

ALTER TABLE chat_threads
  ADD COLUMN IF NOT EXISTS refinement_context JSONB;

COMMENT ON COLUMN chat_threads.refinement_context IS 'Orchestrator-purged plan: { proposed_plan: string[], search_queries: string[] }. Set when user refines (e.g. no limo); loaded at start of next turn.';

COMMIT;
