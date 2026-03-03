# Chat Conversations — ChatGPT-Style UX, AI Auto-Respond & Team Assignment

## Overview

Partner-facing chat inbox with ChatGPT-style layout: left sidebar (conversation list), center (active chat), and assignment to team members. **AI-first support**: When enabled, conversations are auto-answered by AI using storefront knowledge base, FAQs, and order status. Only when escalation is required, the chat is assigned to a human.

---

## UX Layout (ChatGPT-Style)

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: Partner logo | Storefront switcher | User               │
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                    │
│  Left Nav    │  Center: Active Conversation                      │
│  (collapsible)│                                                    │
│              │  ┌──────────────────────────────────────────────┐ │
│  [+ New]     │  │ Messages (scrollable)                         │ │
│              │  │  Customer: ...                                │ │
│  Conversations│  │  Partner: ...                                 │ │
│  ─────────── │  │  ...                                          │ │
│  Conv 1      │  └──────────────────────────────────────────────┘ │
│  Conv 2 ●    │                                                    │
│  Conv 3      │  ┌──────────────────────────────────────────────┐ │
│  ...         │  │ [Assign to: ▼] [Message input...] [Send]     │ │
│              │  └──────────────────────────────────────────────┘ │
│  Filters:    │                                                    │
│  All | Mine  │                                                    │
│  Unassigned  │                                                    │
└──────────────┴──────────────────────────────────────────────────┘
```

- **Left sidebar**: Collapsible; list of conversations with preview/snippet; "New" button; filters (All, Assigned to me, Unassigned).
- **Center**: Message thread for selected conversation; assignee dropdown; message input + send.
- **Responsive**: Sidebar collapses to drawer on mobile; center remains primary.

---

## AI-First Support (Auto-Respond)

### Flow

1. **Feature flag** (per storefront): `ai_auto_respond_enabled`
2. **Incoming message** → Classify (routine vs human-needed)
3. **Routine** + AI enabled → Generate AI response from KB + FAQs + order status → Post as message; no human assignment
4. **Human-needed** (dispute, damage, complex, etc.) → Create escalation; assign to team member; no AI response

### Storefront-Managed Content

| Content | Purpose | Schema |
|---------|---------|--------|
| **Knowledge base** | General articles, policies, how-tos | `storefront_kb_articles` |
| **FAQs** | Q&A pairs for common questions | `storefront_faqs` |
| **Order status templates** | Auto-updates (e.g. "Your order #X has shipped") | Optional: derived from orders or `storefront_order_status_templates` |

### Classification (extend hybrid-response)

- Reuse `classify_message()`: routine → AI; complex/dispute/physical_damage → human
- **Optional**: Add confidence threshold; low-confidence routine → human
- **Optional**: Add "handoff" intent (e.g. "speak to human") → always human

### AI Response Generation

- **Input**: Customer message + conversation context + KB articles + FAQs + order status for linked order/bundle
- **Model**: Azure OpenAI / Gemini (same as orchestrator)
- **Output**: Text response posted as message with `sender_type = 'ai'`
- **Fallback**: If AI fails or returns empty → mark for human; do not post generic error to customer

### Order Scoping & Authorization (Critical)

**Problem**: We must never respond about any order; only the person who placed that order should receive order-specific updates.

**Rules**:

1. **Strict order scope**
   - AI may include order status ONLY for orders linked to this conversation: `conversation.order_id` or `orders` derived from `conversation.bundle_id`.
   - Never look up orders by ID mentioned in free text (e.g. "order #12345"); always use the conversation's linked order/bundle.
   - If conversation has no `order_id` and no `bundle_id`, do NOT include any order-specific info in the response.

2. **Participant verification**
   - Before including order details, verify the order owner is a participant: `order.user_id` IN (SELECT user_id FROM participants WHERE conversation_id = ? AND participant_type = 'customer').
   - If the requester (message sender) cannot be mapped to a participant with `user_id`, do NOT include order-specific info.

3. **Sender resolution**
   - Web: `messages.sender_id` = Clerk user → `users.id` via `users.clerk_user_id`.
   - WhatsApp/chat: Resolve via `chat_thread_mappings` (platform + thread_id → user_id) or `account_links` (platform + platform_user_id → user_id). If no mapping, treat as unverified; do not return order details.

4. **Conversation creation**
   - When creating a conversation from an order: set `conversation.order_id` (or `bundle_id`); add `order.user_id` as participant with `participant_type = 'customer'`.
   - Ensure the channel (web, WhatsApp) is linked to that user before including order data.

5. **LLM prompt constraint**
   - When building context for the AI, pass ONLY the allowed order(s). Instruct the model: "You may only reference these orders. Do not fabricate or infer other order IDs."

6. **API contract**
   - `POST /classify-and-respond` (or similar) accepts: `conversation_id`, `message_content`, `sender_user_id` (optional), `allowed_order_ids` (explicit list).
   - Service MUST NOT fetch orders by any other means; it uses only `allowed_order_ids` for order context.

### Integration Points

- **hybrid-response-service**: Extend `classify-and-route` or add `classify-and-respond` that:
  - Classifies message
  - If route=ai: fetches KB/FAQs/order status, calls LLM, returns suggested response
  - If route=human: returns escalation; portal/conversation API posts response and assigns
- **Conversation API**: When receiving new message, if storefront has `ai_auto_respond_enabled`:
  - Resolve sender to `user_id` (web/WhatsApp mapping); verify sender is a participant
  - Build allowed-order set: conversation.order_id or orders from bundle_id, filtered by `order.user_id IN participants`
  - Call hybrid-response with ONLY this allowed-order context
  - If AI response: insert message with sender_type=ai
  - If human: set `assigned_to_member_id` (or leave unassigned for team to pick)

---

## Schema Changes

### 1. Extend `conversations`

```sql
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS partner_id UUID REFERENCES partners(id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS storefront_id UUID REFERENCES storefronts(id);  -- nullable; add when storefronts exist
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS assigned_to_member_id UUID REFERENCES partner_members(id);
CREATE INDEX idx_conversations_partner_id ON conversations(partner_id);
CREATE INDEX idx_conversations_assigned_to ON conversations(assigned_to_member_id);
```

- Derive `partner_id` from bundle/order when conversation is created.
- `assigned_to_member_id` = partner team member handling the conversation.

### 2. Optional: Link `support_escalations` to conversations

```sql
ALTER TABLE support_escalations ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES conversations(id);
```

- When escalation is created from a conversation, set `conversation_id`.
- Keep `assigned_to` / `assigned_to_clerk_id` for platform admins; `conversations.assigned_to_member_id` for partner team.

### 3. AI Feature Flag & Knowledge Base (storefront or partner)

```sql
-- If storefronts exist
ALTER TABLE storefronts ADD COLUMN IF NOT EXISTS ai_auto_respond_enabled BOOLEAN DEFAULT FALSE;

-- Or on partners (if no storefronts yet)
ALTER TABLE partners ADD COLUMN IF NOT EXISTS ai_auto_respond_enabled BOOLEAN DEFAULT FALSE;

-- Knowledge base articles (partner_id; add storefront_id in storefront migration)
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
CREATE INDEX idx_kb_articles_partner ON partner_kb_articles(partner_id);

-- FAQs (same pattern)
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
CREATE INDEX idx_faqs_partner ON partner_faqs(partner_id);
```

- **Order status**: Fetched from `orders`, `order_legs`, `status_updates` at response time.

### 4. RLS

- Partners see only conversations where `conversations.partner_id` = their partner.
- Filter by `storefront_id` when storefronts are in use.
- KB/FAQs: partner can CRUD only their own.

---

## API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/partners/conversations` | GET | List conversations for partner (with filters: all, mine, unassigned) |
| `/api/partners/conversations` | POST | Create conversation (e.g. from order) |
| `/api/partners/conversations/[id]` | GET | Get conversation + messages |
| `/api/partners/conversations/[id]` | PATCH | Update (e.g. assign) |
| `/api/partners/conversations/[id]/assign` | POST | Assign to team member |
| `/api/partners/conversations/[id]/messages` | GET | List messages (paginated) |
| `/api/partners/conversations/[id]/messages` | POST | Send message (triggers AI flow if enabled) |
| `/api/partners/team` | GET | Already exists; used for assignee dropdown |
| `/api/partners/knowledge-base` | GET, POST | List, create KB articles |
| `/api/partners/knowledge-base/[id]` | GET, PATCH, DELETE | Get, update, delete KB article |
| `/api/partners/faqs` | GET, POST | List, create FAQs |
| `/api/partners/faqs/[id]` | GET, PATCH, DELETE | Get, update, delete FAQ |
| `/api/partners/settings` | PATCH | Add `ai_auto_respond_enabled` to settings |

---

## UI Components

### 1. Layout: `apps/portal/app/(partner)/conversations/layout.tsx`

- Two-column layout: sidebar (w-64 or collapsible) + main (flex-1).
- Sidebar hidden on mobile; toggle button reveals drawer.

### 2. Sidebar: `ConversationSidebar.tsx`

- "New conversation" button.
- List of conversations: `conversation.title` or preview of last message; unread indicator; assignee badge.
- Filters: All | Assigned to me | Unassigned.
- Click item → set active conversation ID in state/URL.

### 3. Center: `ConversationView.tsx`

- Header: conversation title, assignee dropdown (Assign to: [Team member ▼]); badge if AI-handled vs human-assigned.
- Message list: scrollable, grouped by date; sender type (customer, partner, **ai**).
- Message input: textarea + Send.
- Use Supabase Realtime (optional) for new messages.
- **AI response**: When customer sends message and AI is enabled, AI reply appears automatically (or "AI is typing..." indicator).

### 4. Knowledge Base & FAQs Settings

- **Settings or dedicated page**: Toggle "AI auto-respond" (per storefront/partner).
- **Knowledge Base** tab/section: List, add, edit, delete KB articles (title, content).
- **FAQs** tab/section: List, add, edit, delete FAQ pairs (question, answer).
- **Order status**: Auto-included from orders; no manual entry. Optional: "Order status message templates" for custom phrasing.

### 5. State / URL

- Option A: `/conversations` with `?id=xxx` for active conversation.
- Option B: `/conversations/[id]` for cleaner URLs.
- Recommendation: `/conversations` (list) and `/conversations/[id]` (detail) for shareability.

---

## Conversation Creation

- Auto-create when: order placed, bundle created, or customer contacts support.
- Manual "New": partner starts a blank conversation (e.g. for outbound).
- Set `partner_id` from order/bundle or current partner context.

---

## Integration with Storefront Plan

- When storefronts exist: add `storefront_id` to conversations; filter sidebar by storefront.
- Assignee: `storefront_members` instead of `partner_members` when storefronts are used.
- Sidebar can show storefront filter: "Taxi Service" | "Flower Shop".

---

## Key Files

| File | Purpose |
|------|---------|
| `supabase/migrations/20240129000002_conversations_partner_assignment.sql` | Schema: conversations, KB, FAQs, ai_auto_respond_enabled |
| `apps/portal/app/(partner)/conversations/page.tsx` | Main page (layout + sidebar + placeholder) |
| `apps/portal/app/(partner)/conversations/[id]/page.tsx` | Conversation detail + messages |
| `apps/portal/app/(partner)/knowledge-base/page.tsx` | KB articles management (or under Settings) |
| `apps/portal/app/(partner)/faqs/page.tsx` | FAQs management (or under Settings) |
| `apps/portal/components/conversations/ConversationSidebar.tsx` | Left nav |
| `apps/portal/components/conversations/ConversationView.tsx` | Center chat |
| `apps/portal/components/conversations/MessageList.tsx` | Message thread |
| `apps/portal/components/conversations/MessageInput.tsx` | Input + send |
| `apps/portal/components/conversations/AssigneeDropdown.tsx` | Assign to team member |
| `apps/portal/app/api/partners/conversations/route.ts` | List, create |
| `apps/portal/app/api/partners/conversations/[id]/route.ts` | Get, patch |
| `apps/portal/app/api/partners/conversations/[id]/assign/route.ts` | Assign |
| `apps/portal/app/api/partners/conversations/[id]/messages/route.ts` | Get, post messages (triggers AI flow) |
| `apps/portal/app/api/partners/knowledge-base/route.ts` | List, create KB |
| `apps/portal/app/api/partners/knowledge-base/[id]/route.ts` | Get, patch, delete KB |
| `apps/portal/app/api/partners/faqs/route.ts` | List, create FAQs |
| `apps/portal/app/api/partners/faqs/[id]/route.ts` | Get, patch, delete FAQ |
| `services/hybrid-response-service/api/respond.py` | New: classify + AI response generation (or extend classify.py) |
| `services/hybrid-response-service/db.py` | Fetch KB/FAQs; call LLM for response |

---

## Nav Update

- Add "Conversations" (or "Chat") to partner nav (e.g. after Support).
- Add "Knowledge Base" and "FAQs" under Settings, or as separate nav items.
