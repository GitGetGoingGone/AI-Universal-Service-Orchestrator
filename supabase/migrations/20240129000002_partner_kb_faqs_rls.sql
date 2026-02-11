-- Enable RLS on partner_kb_articles and partner_faqs
-- Portal/backend use service_role and bypass RLS; this enables future policy-based access.

BEGIN;

ALTER TABLE IF EXISTS public.partner_kb_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_faqs ENABLE ROW LEVEL SECURITY;

COMMIT;
