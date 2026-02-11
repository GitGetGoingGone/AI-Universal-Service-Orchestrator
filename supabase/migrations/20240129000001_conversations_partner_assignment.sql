-- Migration: Partner Conversations, KB, FAQs, AI Auto-Respond
-- Date: 2024-01-29
-- Dependencies: core_and_scout, orders_and_payments, timechain_recovery_support, partner_portal_production

BEGIN;

-- 1. Extend conversations for partner scope and assignment
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS partner_id UUID REFERENCES partners(id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS assigned_to_member_id UUID REFERENCES partner_members(id);
CREATE INDEX IF NOT EXISTS idx_conversations_partner_id ON conversations(partner_id);
CREATE INDEX IF NOT EXISTS idx_conversations_assigned_to_member ON conversations(assigned_to_member_id);

-- 2. Link support_escalations to conversations
ALTER TABLE support_escalations ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES conversations(id);
CREATE INDEX IF NOT EXISTS idx_support_escalations_conversation ON support_escalations(conversation_id);

-- 3. AI auto-respond flag on partners
ALTER TABLE partners ADD COLUMN IF NOT EXISTS ai_auto_respond_enabled BOOLEAN DEFAULT FALSE;

-- 4. Knowledge base articles
CREATE TABLE IF NOT EXISTS partner_kb_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  sort_order SMALLINT DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_partner_kb_articles_partner ON partner_kb_articles(partner_id);

-- 5. FAQs
CREATE TABLE IF NOT EXISTS partner_faqs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  sort_order SMALLINT DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_partner_faqs_partner ON partner_faqs(partner_id);

COMMIT;
