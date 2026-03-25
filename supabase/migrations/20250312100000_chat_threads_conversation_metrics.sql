-- Per-thread metrics for admin cost dashboard (thought timelines, memory health, credit usage)
BEGIN;

ALTER TABLE chat_threads
  ADD COLUMN IF NOT EXISTS conversation_metrics JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN chat_threads.conversation_metrics IS 'Aggregated multi-agent / chat metrics for platform admin dashboard (JSON).';

COMMIT;
