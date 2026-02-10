-- Enable Row Level Security (RLS) on all public tables exposed to PostgREST.
-- Resolves Supabase linter: rls_disabled_in_public (0013).
--
-- With RLS enabled and no permissive policies, anon and authenticated roles
-- get no access. Backend and portal use the service_role key, which bypasses
-- RLS, so existing server-side access is unchanged.
--
-- Reference: https://supabase.com/docs/guides/database/database-linter?lint=0013_rls_disabled_in_public

BEGIN;

-- PostGIS reference table (if present): allow read-only so spatial lookups work if needed
ALTER TABLE IF EXISTS public.spatial_ref_sys ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'spatial_ref_sys') THEN
    DROP POLICY IF EXISTS "Allow read spatial_ref_sys" ON public.spatial_ref_sys;
    CREATE POLICY "Allow read spatial_ref_sys" ON public.spatial_ref_sys FOR SELECT USING (true);
  END IF;
END $$;

-- Application tables: enable RLS with no policies (anon/authenticated get no rows; service_role bypasses)
ALTER TABLE IF EXISTS public.product_capability_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.capability_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.product_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_manifests ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.manifest_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.intent_graphs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.intent_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.premium_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.bundles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.bundle_legs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.order_legs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.payment_splits ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.escrow_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.escrow_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.escrow_releases ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.time_chains ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.time_chain_legs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.conflict_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.autonomous_recoveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.recovery_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.alternative_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.capacity_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.message_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.negotiations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.status_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.progress_ledgers ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.agent_reasoning_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.negotiation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.communication_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.escalations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.simulated_partners ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.simulated_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.simulated_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.simulation_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.webhook_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.chat_thread_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.account_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.platform_admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.product_availability ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.availability_integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.product_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.payouts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.commission_breaks ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.product_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.product_modifiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.product_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_promotions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_venues ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_service_areas ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.order_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.platform_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partner_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.partners ENABLE ROW LEVEL SECURITY;

COMMIT;
