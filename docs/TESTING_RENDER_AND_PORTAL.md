# Steps to Test All Services (Render + Portal)

End-to-end testing for the full stack: backend services on **Render**, Partner Portal on **Vercel**, including **Chat-First / Link Account** (API response standard, webhook push, Link Account API).

---

## Prerequisites

1. **Deploy backend on Render**  
   Follow [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) through Step 7 so you have:
   - uso-discovery, uso-intent, uso-orchestrator, uso-webhook (required)
   - uso-omnichannel-broker, uso-resourcing, uso-payment (optional for core chat)
   - uso-task-queue, uso-hub-negotiator, uso-hybrid-response (optional; Phase 2 modules)
   - uso-durable (optional)

2. **Apply migrations**  
   Run these on your Supabase project:
   - `supabase/migrations/20240128000012_link_account_support.sql` (adds `users.clerk_user_id`)
   - `supabase/migrations/20240128100003_task_queue_hub_negotiator_hybrid.sql` (for Task Queue, HubNegotiator, Hybrid Response)

3. **Orchestrator env (Render)**  
   On **uso-orchestrator** → Environment, set:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (or `SUPABASE_SECRET_KEY`) – required for Link Account
   - `GOOGLE_OAUTH_CLIENT_ID` – required only for **Google** Link Account (get from [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials → OAuth 2.0 Client ID, type “Web application”)

4. **Webhook env (Render)**  
   On **uso-webhook** → Environment:
   - Without `CHATGPT_WEBHOOK_URL` / `GEMINI_WEBHOOK_URL` / Twilio: push to chat/WhatsApp returns **503** (expected; no stubs).
   - To test successful push: set `CHATGPT_WEBHOOK_URL` or `GEMINI_WEBHOOK_URL` to a URL that accepts POST (e.g. a request bin or your real webhook endpoint).

5. **Portal on Vercel**  
   Deploy `apps/portal` to Vercel per [RENDER_DEPLOYMENT.md § Partner Portal](./RENDER_DEPLOYMENT.md#partner-portal-vercel). Set env vars (see **Portal environment variables** below).

---

## 1. Set your base URLs

Replace with your actual Render (and optional Vercel) URLs:

```bash
export ORCHESTRATOR="https://uso-orchestrator.onrender.com"
export DISCOVERY="https://uso-discovery.onrender.com"
export INTENT="https://uso-intent.onrender.com"
export WEBHOOK="https://uso-webhook.onrender.com"
export PORTAL_URL="https://your-portal.vercel.app"   # if using Vercel

# Optional: Phase 2 modules (Task Queue, HubNegotiator, Hybrid Response)
export TASK_QUEUE="https://uso-task-queue.onrender.com"
export HUB_NEGOTIATOR="https://uso-hub-negotiator.onrender.com"
export HYBRID_RESPONSE="https://uso-hybrid-response.onrender.com"
```

---

## 2. Health and warmup (avoid cold starts)

On Render free tier, services sleep after ~15 min. Warm them first:

```bash
./scripts/health-and-warmup.sh
```

With chat E2E and webhook:

```bash
./scripts/health-and-warmup.sh --e2e --webhook
```

Or manually warm core services:

```bash
curl -s --max-time 90 "$ORCHESTRATOR/health"
curl -s --max-time 90 "$DISCOVERY/health"
curl -s --max-time 90 "$INTENT/health"
curl -s --max-time 90 "$WEBHOOK/health"
# Optional: Phase 2 modules
curl -s --max-time 90 "$TASK_QUEUE/health"
curl -s --max-time 90 "$HUB_NEGOTIATOR/health"
curl -s --max-time 90 "$HYBRID_RESPONSE/health"
```

---

## 3. Chat-First API (orchestrator)

**3.1 Standard response shape (data, machine_readable, adaptive_card, metadata)**

```bash
curl -s -X POST "$ORCHESTRATOR/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"text": "find flowers"}' | jq 'keys'
```

Expected: `["data", "summary", "machine_readable", "adaptive_card", "metadata"]` (and optionally `agent_reasoning`).

**3.2 machine_readable (JSON-LD)**

```bash
curl -s -X POST "$ORCHESTRATOR/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"text": "find flowers"}' | jq '.machine_readable'
```

Expected: object with `"@context": "https://schema.org"` and e.g. `"@type": "ItemList"` or product-like structure.

**3.3 adaptive_card**

```bash
curl -s -X POST "$ORCHESTRATOR/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"text": "find flowers"}' | jq '.adaptive_card.type, .adaptive_card.version'
```

Expected: `"AdaptiveCard"` and `"1.5"`.

**3.4 With thread_id + platform (for webhook mapping)**

```bash
curl -s -X POST "$ORCHESTRATOR/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"text": "find cakes", "thread_id": "thread-abc", "platform": "chatgpt"}'
```

Then call webhook mappings (see step 5) to confirm the mapping was registered.

**3.5 With platform_user_id (Link Account resolution)**

If you have linked an account (step 6), send the same `platform_user_id` and `platform` you used when linking; the response should be the same, and internal `user_id` will be resolved from `account_links`.

```bash
curl -s -X POST "$ORCHESTRATOR/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"text": "find flowers", "platform_user_id": "YOUR_OPENAI_USER_ID", "platform": "openai"}'
```

---

## 4. Intent service (JSON-LD)

```bash
curl -s -X POST "$INTENT/api/v1/resolve" \
  -H "Content-Type: application/json" \
  -d '{"text": "I want to send flowers"}' | jq '{ data: .data, machine_readable: .machine_readable | keys, metadata: .metadata }'
```

Expected: `data`, `machine_readable` (with `@context`, `@type`, `result`), `metadata` with `request_id`, `api_version`, `timestamp`.

---

## 5. Discovery service (products + cards)

```bash
curl -s "$DISCOVERY/api/v1/discover?intent=cakes&limit=5" | jq '{ data: .data | keys, machine_readable: .machine_readable | keys, adaptive_card: .adaptive_card | type }'
```

Expected: `data` (products, count), `machine_readable` (ItemList/product structure), `adaptive_card` (object).

---

## 5b. Discovery features (ACP / UCP)

These endpoints support **ChatGPT (ACP)** and **Gemini (UCP)** catalog discovery. Use your deployed discovery base URL (`$DISCOVERY`). For push and push-status you need a valid `partner_id` from your `partners` table.

**5b.1 UCP Business Profile (well-known)**

```bash
curl -s "$DISCOVERY/.well-known/ucp" | jq '{ ucp: .ucp.version, endpoint: .ucp.services["dev.ucp.shopping"].rest.endpoint }'
```

Expected: `ucp.version` (e.g. `"2026-01-11"`), `endpoint` containing `/api/v1/ucp`.

**5b.2 UCP catalog (items)**

```bash
curl -s "$DISCOVERY/api/v1/ucp/items?q=flowers&limit=3" | jq '{ item_count: (.items | length), first: .items[0] | keys }'
```

Expected: `items` array; each item has `id`, `title`, `price` (integer cents), optional `image_url`, `seller_name`.

**5b.3 ACP feed (public JSON Lines)**

```bash
curl -s "$DISCOVERY/api/v1/feeds/acp" | head -1 | jq .
```

Expected: First line is a single JSON object with ACP fields (`item_id`, `title`, `description`, `url`, `image_url`, `price`, `availability`, `brand`, `seller_name`, `seller_url`, etc.). Optional: `?partner_id=<uuid>` to filter by partner.

**5b.4 Push status (15-minute throttle)**

Replace `PARTNER_UUID` with a real partner id from your `partners` table:

```bash
curl -s "$DISCOVERY/api/v1/feeds/push-status?partner_id=PARTNER_UUID" | jq .
```

Expected: `{ "next_acp_push_allowed_at": "<ISO8601>" }` or `null` if no recent push.

**5b.5 Push to ChatGPT / Gemini**

Same `PARTNER_UUID`; optionally use a real `product_id` for scope `single`:

```bash
# Push entire catalog for partner to both targets
curl -s -X POST "$DISCOVERY/api/v1/feeds/push" \
  -H "Content-Type: application/json" \
  -d '{"scope":"all","targets":["chatgpt","gemini"],"partner_id":"PARTNER_UUID"}' | jq .
```

Expected: 200 with e.g. `chatgpt: "pushed"`, `next_acp_push_allowed_at`, `rows_pushed`, `gemini: "validated"`, `ucp_compliant`, `ucp_non_compliant`. Calling again within 15 minutes for ChatGPT returns **429** with `error: "rate_limited"` and `next_allowed_at`.

**5b.6 Validate product for discovery**

Replace `PRODUCT_UUID` with a real product id:

```bash
curl -s "$DISCOVERY/api/v1/products/PRODUCT_UUID/validate-discovery" | jq '{ acp: .acp.valid, ucp: .ucp.valid, acp_errors: .acp.errors, ucp_errors: .ucp.errors }'
```

Expected: `acp.valid`, `ucp.valid` (booleans), optional `acp.errors`, `ucp.errors` arrays.

---

## 6. Webhook service (no stubs)

**6.1 Register a mapping (must succeed if Supabase configured)**

```bash
curl -s -X POST "$WEBHOOK/api/v1/webhooks/mappings" \
  -H "Content-Type: application/json" \
  -d '{"platform": "chatgpt", "thread_id": "test-thread-123", "user_id": null, "platform_user_id": null}' | jq .
```

Expected: `{"status": "registered", "platform": "chatgpt", "thread_id": "test-thread-123", ...}`.

**6.2 Push to chat (503 when not configured)**

If you have **not** set `CHATGPT_WEBHOOK_URL` on uso-webhook:

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST "$WEBHOOK/api/v1/webhooks/chat/chatgpt/test-thread-123" \
  -H "Content-Type: application/json" \
  -d '{"narrative": "Test update"}'
```

Expected: **503** (no stub success).

If you **have** set `CHATGPT_WEBHOOK_URL` to a valid endpoint:

```bash
curl -s -X POST "$WEBHOOK/api/v1/webhooks/chat/chatgpt/test-thread-123" \
  -H "Content-Type: application/json" \
  -d '{"narrative": "Test update", "adaptive_card": null}' | jq .
```

Expected: `{"status": "delivered", ...}` (or 502 if the remote URL fails).

**6.3 Push to Gemini (503 when not configured)**

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST "$WEBHOOK/api/v1/webhooks/chat/gemini/test-thread-456" \
  -H "Content-Type: application/json" \
  -d '{"narrative": "Test"}'
```

Expected: **503** unless `GEMINI_WEBHOOK_URL` is set.

---

## 7. Link Account API

**7.1 Link status (requires user_id)**

```bash
# Replace USER_UUID with a real user id from your Supabase users table
curl -s "$ORCHESTRATOR/api/v1/link-account/status?user_id=USER_UUID" | jq .
```

Expected: `{"data": {"user_id": "...", "linked_platforms": [...]}, "machine_readable": {...}, "metadata": {...}}`. If the user has no links, `linked_platforms` is `[]`.

**7.2 Link Google (requires GOOGLE_OAUTH_CLIENT_ID + valid id_token)**

You need a real Google OAuth2 `id_token` (from your frontend or a test OAuth flow). With a valid token:

```bash
curl -s -X POST "$ORCHESTRATOR/api/v1/link-account" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "id_token": "YOUR_GOOGLE_ID_TOKEN",
    "clerk_user_id": "optional-clerk-user-id"
  }' | jq .
```

Expected: `{"data": {"linked": true, "provider": "google", "platform_user_id": "...", "user_id": "..."}, ...}`.  
Without `GOOGLE_OAUTH_CLIENT_ID` or with invalid token: **401** or **400**.

**7.3 Link OpenAI (ChatGPT) – no OAuth; requires clerk_user_id**

Used when the user has signed in via Clerk (e.g. on the portal) and wants to link their ChatGPT identity:

```bash
curl -s -X POST "$ORCHESTRATOR/api/v1/link-account" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "platform_user_id": "chatgpt-session-user-id-from-client",
    "clerk_user_id": "user_xxxx_from_clerk"
  }' | jq .
```

Expected: `{"data": {"linked": true, "provider": "openai", ...}, ...}`.  
Without `clerk_user_id`: **400** (required for openai).

---

## 8. Agentic consent and handoff

```bash
curl -s "$ORCHESTRATOR/api/v1/agentic-consent" | jq .
curl -s "$ORCHESTRATOR/api/v1/agentic-handoff" | jq .
```

Expected: consent returns scope and allowed_actions; handoff returns `configured: true/false` and Clerk keys when set.

---

## 8b. Phase 2 modules (Task Queue, HubNegotiator, Hybrid Response)

Requires migration `20240128100003_task_queue_hub_negotiator_hybrid.sql` and deployed services. Set `$TASK_QUEUE`, `$HUB_NEGOTIATOR`, `$HYBRID_RESPONSE` as in section 1.

### 8b.1 Multi-Vendor Task Queue (Module 11)

Replace `ORDER_UUID` and `PARTNER_UUID` with real ids from `orders` and `partners` tables:

```bash
# Create tasks for an order (idempotent)
curl -s -X POST "$TASK_QUEUE/api/v1/orders/ORDER_UUID/tasks" | jq .

# List partner's tasks (pending only if earlier tasks in order are completed)
curl -s "$TASK_QUEUE/api/v1/tasks?partner_id=PARTNER_UUID&status=pending" | jq .

# Start / complete a task (replace TASK_UUID)
curl -s -X POST "$TASK_QUEUE/api/v1/tasks/TASK_UUID/start?partner_id=PARTNER_UUID" | jq .
curl -s -X POST "$TASK_QUEUE/api/v1/tasks/TASK_UUID/complete?partner_id=PARTNER_UUID" -H "Content-Type: application/json" -d '{}' | jq .
```

Expected: create returns tasks array; list returns partner tasks; start/complete return updated task with `status`, `started_at`, `completed_at`.

### 8b.2 HubNegotiator & Bidding (Module 10)

Replace `ORDER_UUID`, `BUNDLE_UUID`, `PARTNER_UUID` with real ids:

```bash
# Create RFP
curl -s -X POST "$HUB_NEGOTIATOR/api/v1/rfps" -H "Content-Type: application/json" \
  -d '{"order_id":"ORDER_UUID","bundle_id":"BUNDLE_UUID","request_type":"assembly","title":"Assemble bundle","deadline":"2026-02-15T18:00:00Z","compensation_cents":5000}' | jq .

# List RFPs
curl -s "$HUB_NEGOTIATOR/api/v1/rfps?status=open" | jq .

# Submit bid (replace RFP_UUID)
curl -s -X POST "$HUB_NEGOTIATOR/api/v1/rfps/RFP_UUID/bids" -H "Content-Type: application/json" \
  -d '{"hub_partner_id":"PARTNER_UUID","amount_cents":4500,"proposed_completion_at":"2026-02-10T12:00:00Z"}' | jq .

# Select winning bid (replace BID_UUID)
curl -s -X POST "$HUB_NEGOTIATOR/api/v1/rfps/RFP_UUID/select-winner" -H "Content-Type: application/json" \
  -d '{"bid_id":"BID_UUID"}' | jq .

# Add hub capacity
curl -s -X POST "$HUB_NEGOTIATOR/api/v1/hub-capacity" -H "Content-Type: application/json" \
  -d '{"partner_id":"PARTNER_UUID","available_from":"2026-02-01T00:00:00Z","available_until":"2026-02-28T23:59:59Z","capacity_slots":5}' | jq .
```

Expected: create RFP returns `id`, `status: open`; bid returns `id`, `status: submitted`; select-winner returns RFP with `winning_bid_id`, `status: closed`; hub-capacity returns inserted row.

### 8b.3 Hybrid Response Logic (Module 13)

```bash
# Classify and route (routine -> AI, complex/dispute/physical_damage -> human)
curl -s -X POST "$HYBRID_RESPONSE/api/v1/classify-and-route" -H "Content-Type: application/json" \
  -d '{"conversation_ref":"conv-abc","message_content":"Where is my order?"}' | jq .
```

Expected: `{ "classification": "routine", "route": "ai", "support_escalation_id": null }` for routine queries.

```bash
# Human route (creates support_escalation)
curl -s -X POST "$HYBRID_RESPONSE/api/v1/classify-and-route" -H "Content-Type: application/json" \
  -d '{"conversation_ref":"conv-xyz","message_content":"My order arrived damaged and I want a refund"}' | jq .
```

Expected: `{ "classification": "physical_damage" or "dispute", "route": "human", "support_escalation_id": "<uuid>" }`.

```bash
# List escalations
curl -s "$HYBRID_RESPONSE/api/v1/escalations?status=pending" | jq .

# Assign (replace ESCALATION_UUID and USER_UUID)
curl -s -X POST "$HYBRID_RESPONSE/api/v1/escalations/ESCALATION_UUID/assign" -H "Content-Type: application/json" \
  -d '{"assigned_to":"USER_UUID"}' | jq .

# Resolve
curl -s -X POST "$HYBRID_RESPONSE/api/v1/escalations/ESCALATION_UUID/resolve" -H "Content-Type: application/json" \
  -d '{"resolution_notes":"Refund issued"}' | jq .
```

Expected: list returns `escalations` array; assign returns escalation with `status: assigned`; resolve returns `status: resolved`, `resolved_at`.

---

## 9. Partner Portal (Vercel)

The portal is a Next.js app; per the deployment doc it is deployed on **Vercel**, not Render.

### Portal environment variables

Use the same names in **Vercel** (and in local `apps/portal/.env.local`) so config matches across environments:

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk publishable key (client) |
| `CLERK_SECRET_KEY` | Clerk secret key (server) |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon/publishable key (client, RLS) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server, bypasses RLS) |
| `DISCOVERY_SERVICE_URL` | Discovery service base URL (for validate-discovery and feed push proxy; e.g. `https://uso-discovery.onrender.com`) |
| `TASK_QUEUE_SERVICE_URL` | Task Queue service (for partner Tasks page; e.g. `https://uso-task-queue.onrender.com`) |
| `HUB_NEGOTIATOR_SERVICE_URL` | Hub Negotiator service (for partner Hub RFPs and platform RFPs; e.g. `https://uso-hub-negotiator.onrender.com`) |

The portal also accepts these **alternate names** (so existing `.env.local` with the older names still works): `SUPABASE_PUBLISHABLE_KEY` instead of `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `SUPABASE_SECRET_KEY` instead of `SUPABASE_SERVICE_ROLE_KEY`. For new setups and Vercel, prefer the names in the table above (same as [RENDER_DEPLOYMENT.md § Partner Portal](./RENDER_DEPLOYMENT.md#partner-portal-vercel)).

### Test steps

1. **Open the portal**  
   `https://your-portal.vercel.app` (or your Vercel URL).

2. **Sign in with Clerk**  
   Use the Clerk sign-in/sign-up flow (ensure `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` are set).

3. **Dashboard**  
   After sign-in, you should see the partner dashboard (orders today, earnings, alerts) if your user is linked to a partner (e.g. by `contact_email` in `partners` or `partner_members`).

4. **Products**  
   If you have partner context, use the nav to open Products and confirm list/create/edit work against Supabase.

5. **Settings**  
   Open Settings and confirm the page loads. In **Commerce profile (AI catalog)** you can edit seller fields (seller name, seller URL, return/privacy/terms URLs, store country, target countries) and save via PATCH /api/partners/me. These are used for ChatGPT and Gemini discovery.
6. **Push to AI catalog (Products)**  
   In the nav, open **Products**. At the top you should see **Push to AI catalog**: buttons **Push to ChatGPT**, **Push to Gemini**, **Push to both**. If the partner has pushed to ChatGPT within the last 15 minutes, the ChatGPT (and "Push to both") button is disabled and a message shows next update time. After a successful push, the message shows Push completed and the product table refreshes with **Last pushed** and **Status** (Success/Failed) per product. Ensure `DISCOVERY_SERVICE_URL` is set in the portal env.

7. **Product edit – ACP/UCP fields and validation**  
   Open **Products**, pick a product, Edit. Confirm: **Fields** (Product URL, Brand, Image URL, Eligible for search (AI discovery), Eligible for checkout, Availability); save and reload to persist. **Validate for discovery**: Click Validate for discovery; the UI calls GET /api/products/{id}/validate-discovery (proxied to the discovery service). You should see Ready for ChatGPT / Ready for Gemini or errors/warnings (requires `DISCOVERY_SERVICE_URL`). **Push to AI catalog**: Section Push to AI catalog with Push to ChatGPT, Push to Gemini, Push to both for this product only (scope=single); same 15-minute throttle for ChatGPT.

### Discovery features – full test flow

Use this flow to verify discovery (ACP/UCP) end-to-end from portal and API.

**Prerequisites**

- Portal env: `DISCOVERY_SERVICE_URL` set to your discovery service (e.g. `https://uso-discovery.onrender.com`).
- At least one **partner** with `verification_status = 'approved'` and a **product** in the DB (created via portal or API).
- Discovery service deployed and healthy (`curl -s $DISCOVERY/health` returns 200).

**Step 1 – Commerce profile (seller attribution)**

1. Sign in to the portal with a user linked to that partner (same email as `partners.contact_email` or in `partner_members`).
2. Go to **Settings** → **Commerce profile (AI catalog)**.
3. Fill in: Business name, Seller name (display), Seller URL, Return policy URL, Privacy policy URL, Terms URL, Store country (e.g. `US`), Target countries (e.g. `US, CA`).
4. Click **Save commerce profile**. Expect "Saved." and no errors.
5. _(Optional)_ Verify via API: `curl -s "$PORTAL_URL/api/partners/me"` (with auth) should return partner object including `seller_name`, `seller_url`, etc.

**Step 2 – Product ACP/UCP fields**

1. Go to **Products** → open a product → **Edit**.
2. Set **Product URL** (e.g. your product page), **Brand**, **Image URL** (main image).
3. Check **Eligible for search (AI discovery)** and, if you support checkout, **Eligible for checkout**.
4. Set **Availability** (e.g. In stock).
5. Click **Save**. Reload the page and confirm values persist.
6. Click **Validate for discovery**. Expect either "Ready for ChatGPT" / "Ready for Gemini" or a list of errors (e.g. missing URL, prohibited content). Resolve errors and validate again until both show ready if desired.

**Step 3 – Products page (push catalog)**

1. Go to **Products** in the nav.
2. In the **Push to AI catalog** section, use **Push entire catalog** (the default; no product selector).
3. Click **Push to ChatGPT**. Expect "Push completed." or, if you pushed recently, "ChatGPT catalog can be updated again at &lt;time&gt;" with the ChatGPT (and "Push to both") button disabled.
4. Click **Push to Gemini**. Expect "Push completed." and a success message (no rate limit for Gemini).
5. Click **Push to both** (when not throttled). Expect 200 and both chatgpt and gemini result keys.
6. Within 15 minutes, click **Push to ChatGPT** again; expect the button to be disabled and the next-allowed time message.

**Step 4 – Verify from API (optional)**

Using your discovery base URL (`$DISCOVERY`) and a real `PARTNER_UUID` / `PRODUCT_UUID`:

- **UCP well-known:** `curl -s "$DISCOVERY/.well-known/ucp" | jq .` — expect `ucp.version` and `rest.endpoint` with `/api/v1/ucp`.
- **UCP catalog:** `curl -s "$DISCOVERY/api/v1/ucp/items?q=flowers&limit=3" | jq .items` — expect array of items with `id`, `title`, `price` (cents), optional `image_url`, `seller_name`.
- **ACP feed:** `curl -s "$DISCOVERY/api/v1/feeds/acp" | head -1 | jq .` — expect one JSON object per line with `item_id`, `title`, `url`, `price`, `seller_name`, etc. Use `?partner_id=PARTNER_UUID` to filter.
- **Push status:** `curl -s "$DISCOVERY/api/v1/feeds/push-status?partner_id=PARTNER_UUID" | jq .` — expect `next_acp_push_allowed_at` (ISO or null).
- **Validate product:** `curl -s "$DISCOVERY/api/v1/products/PRODUCT_UUID/validate-discovery" | jq '{ acp: .acp.valid, ucp: .ucp.valid, acp_errors: .acp.errors }'` — expect `acp.valid`, `ucp.valid`, and any errors.

**Step 5 – Product page push (single product)**

1. Go to **Products** → open a product.
2. Scroll to **Push to AI catalog**.
3. Click **Push to ChatGPT** (or **Push to Gemini** / **Push to both**). Expect success or 15-min throttle message for ChatGPT.
4. Confirm the link "Push entire catalog" on the product edit page takes you to the Products page.

**Discovery quick checklist**

| Check | Where | Pass condition |
|-------|--------|----------------|
| Commerce profile saves | Settings → Commerce profile | Save succeeds; GET /api/partners/me returns seller fields |
| Product ACP/UCP fields persist | Product edit form | URL, brand, image_url, eligibility, availability save and reload |
| Validate for discovery | Product edit → Validate for discovery | Shows Ready for ChatGPT / Gemini or errors (proxy uses DISCOVERY_SERVICE_URL) |
| Push status and 15-min throttle | Products → Push to AI catalog | Push to ChatGPT works once; within 15 min button disabled and message shown |
| Push to Gemini | Products → Push to AI catalog | Push to Gemini returns success (no throttle) |
| Push to both | Products → Push to AI catalog | Both targets updated when not throttled |
| Per-product last pushed / status | Products table | Last pushed column and Status (Success/Failed) after push |
| Single-product push | Product edit → Push to AI catalog | Push to ChatGPT/Gemini/both works for that product (scope=single) |

8. **Link Account from portal (optional)**  
   If you add a “Link ChatGPT” or “Link Google” button on the portal, it would call `POST $ORCHESTRATOR/api/v1/link-account` with the appropriate `id_token` or `platform_user_id` and `clerk_user_id` (from Clerk session). Testing that is the same as step 7 (Link Account API), with `clerk_user_id` taken from your Clerk user id in the browser.

---

## 10. One-shot script (copy-paste)

Replace `ORCHESTRATOR`, `DISCOVERY`, `INTENT`, `WEBHOOK` (and optional `TASK_QUEUE`, `HUB_NEGOTIATOR`, `HYBRID_RESPONSE`) and run:

```bash
ORCHESTRATOR="https://uso-orchestrator.onrender.com"
DISCOVERY="https://uso-discovery.onrender.com"
INTENT="https://uso-intent.onrender.com"
WEBHOOK="https://uso-webhook.onrender.com"
TASK_QUEUE="${TASK_QUEUE:-https://uso-task-queue.onrender.com}"
HUB_NEGOTIATOR="${HUB_NEGOTIATOR:-https://uso-hub-negotiator.onrender.com}"
HYBRID_RESPONSE="${HYBRID_RESPONSE:-https://uso-hybrid-response.onrender.com}"

echo "1. Warmup"
curl -s --max-time 90 "$ORCHESTRATOR/health" > /dev/null
curl -s --max-time 90 "$DISCOVERY/health" > /dev/null
curl -s --max-time 90 "$INTENT/health" > /dev/null
curl -s --max-time 90 "$WEBHOOK/health" > /dev/null
curl -s --max-time 90 "$TASK_QUEUE/health" > /dev/null || true
curl -s --max-time 90 "$HUB_NEGOTIATOR/health" > /dev/null || true
curl -s --max-time 90 "$HYBRID_RESPONSE/health" > /dev/null || true

echo "2. Chat (response shape)"
curl -s -X POST "$ORCHESTRATOR/api/v1/chat" -H "Content-Type: application/json" -d '{"text":"flowers"}' | jq 'keys'

echo "3. Intent (JSON-LD)"
curl -s -X POST "$INTENT/api/v1/resolve" -H "Content-Type: application/json" -d '{"text":"flowers"}' | jq '.machine_readable["@type"]'

echo "4. Discovery (products + card)"
curl -s "$DISCOVERY/api/v1/discover?intent=cakes&limit=2" | jq '.adaptive_card.type'

echo "4b. Discovery UCP well-known"
curl -s "$DISCOVERY/.well-known/ucp" | jq '.ucp.version'
echo "4c. Discovery ACP feed (first line)"
curl -s "$DISCOVERY/api/v1/feeds/acp" | head -1 | jq -c 'keys | length'

echo "5. Webhook mapping"
curl -s -X POST "$WEBHOOK/api/v1/webhooks/mappings" -H "Content-Type: application/json" -d '{"platform":"chatgpt","thread_id":"t-1"}' | jq '.status'

echo "6. Webhook push (expect 503 if CHATGPT_WEBHOOK_URL not set)"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "$WEBHOOK/api/v1/webhooks/chat/chatgpt/t-1" -H "Content-Type: application/json" -d '{"narrative":"Hi"}'

echo "7. Agentic consent"
curl -s "$ORCHESTRATOR/api/v1/agentic-consent" | jq '.scope'

echo "8. Phase 2: Task Queue health"
curl -s --max-time 90 "$TASK_QUEUE/health" | jq '.status' || echo " (skip if not deployed)"
echo "9. Phase 2: Hub Negotiator health"
curl -s --max-time 90 "$HUB_NEGOTIATOR/health" | jq '.status' || echo " (skip if not deployed)"
echo "10. Phase 2: Hybrid Response classify-and-route"
curl -s -X POST "$HYBRID_RESPONSE/api/v1/classify-and-route" -H "Content-Type: application/json" \
  -d '{"conversation_ref":"t","message_content":"order status"}' | jq '.route' || echo " (skip if not deployed)"
```

---

## Checklist summary

| Area | What to test | Pass condition |
|------|----------------|----------------|
| Chat-First response | POST /api/v1/chat | Response has `data`, `machine_readable`, `adaptive_card`, `metadata` |
| Intent JSON-LD | POST /api/v1/resolve | `machine_readable` has `@context`, `@type`, `result` |
| Discovery | GET /api/v1/discover | `machine_readable` + `adaptive_card` present |
| UCP well-known | GET /.well-known/ucp | 200, `ucp.version`, rest endpoint |
| UCP catalog | GET /api/v1/ucp/items?q=... | 200, `items` with id, title, price (cents) |
| ACP feed | GET /api/v1/feeds/acp | 200, JSON Lines, ACP fields per line |
| Push status | GET /api/v1/feeds/push-status?partner_id= | 200, `next_acp_push_allowed_at` |
| Push (ChatGPT/Gemini) | POST /api/v1/feeds/push | 200 or 429 (rate limit); chatgpt/gemini keys |
| Validate discovery | GET /api/v1/products/{id}/validate-discovery | 200, `acp.valid`, `ucp.valid` |
| Webhook mapping | POST /api/v1/webhooks/mappings | 200, `status: registered` |
| Webhook push (unconfigured) | POST /api/v1/webhooks/chat/chatgpt/... | 503 |
| Link Account status | GET /api/v1/link-account/status?user_id=... | 200, `linked_platforms` in data |
| Link Account Google | POST /api/v1/link-account (google + id_token) | 200 and `linked: true` or 401 if invalid |
| Link Account OpenAI | POST /api/v1/link-account (openai + platform_user_id + clerk_user_id) | 200 and `linked: true` |
| Portal | Sign in, dashboard, products, settings | Pages load; no stub placeholders |
| Portal Commerce profile | Settings → Commerce profile | Form loads; PATCH /api/partners/me saves seller fields |
| Portal Push (Products) | Products → Push to AI catalog + table Last pushed/Status | Push to ChatGPT/Gemini/both; 15-min throttle; per-product status |
| Portal product ACP/UCP | Product edit → URL, brand, eligibility, Validate, Push | Fields persist; validate shows ACP/UCP result; push works (scope=single) |
| Task Queue (Module 11) | POST /api/v1/orders/{id}/tasks, GET /api/v1/tasks, start/complete | Creates tasks from order legs; partner list; start/complete updates status |
| HubNegotiator (Module 10) | RFPs, bids, select-winner, hub-capacity | Create RFP; submit bid; select winner; add capacity |
| Hybrid Response (Module 13) | POST /api/v1/classify-and-route, escalations assign/resolve | routine→AI, complex/dispute/damage→human; support_escalations CRUD |

See [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) for deploy steps and env vars; [AI_PLATFORM_PRODUCT_DISCOVERY.md](./AI_PLATFORM_PRODUCT_DISCOVERY.md) for ACP/UCP discovery.

**Real-life scenario:** [REAL_LIFE_TEST_SCENARIO.md](./REAL_LIFE_TEST_SCENARIO.md) – End-to-end test of Task Queue, HubNegotiator, and Hybrid Response with a gift bundle (flowers + chocolates) use case.
