# Steps to Test All Services (Render + Portal)

End-to-end testing for the full stack: backend services on **Render**, Partner Portal on **Vercel**, including **Chat-First / Link Account** (API response standard, webhook push, Link Account API).

---

## Prerequisites

1. **Deploy backend on Render**  
   Follow [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) through Step 7 so you have:
   - uso-discovery, uso-intent, uso-orchestrator, uso-webhook (required)
   - uso-omnichannel-broker, uso-resourcing, uso-payment (optional for core chat)
   - uso-durable (optional)

2. **Apply migration for Link Account**  
   Run `supabase/migrations/20240128000012_link_account_support.sql` on your Supabase project (adds `users.clerk_user_id`).

3. **Orchestrator env (Render)**  
   On **uso-orchestrator** → Environment, set:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (or `SUPABASE_SECRET_KEY`) – required for Link Account
   - `GOOGLE_OAUTH_CLIENT_ID` – required only for **Google** Link Account (get from [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials → OAuth 2.0 Client ID, type “Web application”)

4. **Webhook env (Render)**  
   On **uso-webhook** → Environment:
   - Without `CHATGPT_WEBHOOK_URL` / `GEMINI_WEBHOOK_URL` / Twilio: push to chat/WhatsApp returns **503** (expected; no stubs).
   - To test successful push: set `CHATGPT_WEBHOOK_URL` or `GEMINI_WEBHOOK_URL` to a URL that accepts POST (e.g. a request bin or your real webhook endpoint).

5. **Portal on Vercel**  
   Deploy `apps/portal` to Vercel per [RENDER_DEPLOYMENT.md § Partner Portal](./RENDER_DEPLOYMENT.md#partner-portal-vercel). Set Clerk and Supabase env vars.

---

## 1. Set your base URLs

Replace with your actual Render (and optional Vercel) URLs:

```bash
export ORCHESTRATOR="https://uso-orchestrator.onrender.com"
export DISCOVERY="https://uso-discovery.onrender.com"
export INTENT="https://uso-intent.onrender.com"
export WEBHOOK="https://uso-webhook.onrender.com"
export PORTAL_URL="https://your-portal.vercel.app"   # if using Vercel
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

## 9. Partner Portal (Vercel)

The portal is a Next.js app; per the deployment doc it is deployed on **Vercel**, not Render.

1. **Open the portal**  
   `https://your-portal.vercel.app` (or your Vercel URL).

2. **Sign in with Clerk**  
   Use the Clerk sign-in/sign-up flow (ensure `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` are set in Vercel).

3. **Dashboard**  
   After sign-in, you should see the partner dashboard (orders today, earnings, alerts) if your user is linked to a partner (e.g. by `contact_email` in `partners` or `partner_members`).

4. **Products**  
   If you have partner context, use the nav to open Products and confirm list/create/edit work against Supabase.

5. **Settings**  
   Open Settings and confirm the page loads (no “coming soon” stub if removed).

6. **Link Account from portal (optional)**  
   If you add a “Link ChatGPT” or “Link Google” button on the portal, it would call `POST $ORCHESTRATOR/api/v1/link-account` with the appropriate `id_token` or `platform_user_id` and `clerk_user_id` (from Clerk session). Testing that is the same as step 7, with `clerk_user_id` taken from your Clerk user id in the browser.

---

## 10. One-shot script (copy-paste)

Replace `ORCHESTRATOR`, `DISCOVERY`, `INTENT`, `WEBHOOK` and run:

```bash
ORCHESTRATOR="https://uso-orchestrator.onrender.com"
DISCOVERY="https://uso-discovery.onrender.com"
INTENT="https://uso-intent.onrender.com"
WEBHOOK="https://uso-webhook.onrender.com"

echo "1. Warmup"
curl -s --max-time 90 "$ORCHESTRATOR/health" > /dev/null
curl -s --max-time 90 "$DISCOVERY/health" > /dev/null
curl -s --max-time 90 "$INTENT/health" > /dev/null
curl -s --max-time 90 "$WEBHOOK/health" > /dev/null

echo "2. Chat (response shape)"
curl -s -X POST "$ORCHESTRATOR/api/v1/chat" -H "Content-Type: application/json" -d '{"text":"flowers"}' | jq 'keys'

echo "3. Intent (JSON-LD)"
curl -s -X POST "$INTENT/api/v1/resolve" -H "Content-Type: application/json" -d '{"text":"flowers"}' | jq '.machine_readable["@type"]'

echo "4. Discovery (products + card)"
curl -s "$DISCOVERY/api/v1/discover?intent=cakes&limit=2" | jq '.adaptive_card.type'

echo "5. Webhook mapping"
curl -s -X POST "$WEBHOOK/api/v1/webhooks/mappings" -H "Content-Type: application/json" -d '{"platform":"chatgpt","thread_id":"t-1"}' | jq '.status'

echo "6. Webhook push (expect 503 if CHATGPT_WEBHOOK_URL not set)"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "$WEBHOOK/api/v1/webhooks/chat/chatgpt/t-1" -H "Content-Type: application/json" -d '{"narrative":"Hi"}'

echo "7. Agentic consent"
curl -s "$ORCHESTRATOR/api/v1/agentic-consent" | jq '.scope'
```

---

## Checklist summary

| Area | What to test | Pass condition |
|------|----------------|----------------|
| Chat-First response | POST /api/v1/chat | Response has `data`, `machine_readable`, `adaptive_card`, `metadata` |
| Intent JSON-LD | POST /api/v1/resolve | `machine_readable` has `@context`, `@type`, `result` |
| Discovery | GET /api/v1/discover | `machine_readable` + `adaptive_card` present |
| Webhook mapping | POST /api/v1/webhooks/mappings | 200, `status: registered` |
| Webhook push (unconfigured) | POST /api/v1/webhooks/chat/chatgpt/... | 503 |
| Link Account status | GET /api/v1/link-account/status?user_id=... | 200, `linked_platforms` in data |
| Link Account Google | POST /api/v1/link-account (google + id_token) | 200 and `linked: true` or 401 if invalid |
| Link Account OpenAI | POST /api/v1/link-account (openai + platform_user_id + clerk_user_id) | 200 and `linked: true` |
| Portal | Sign in, dashboard, products, settings | Pages load; no stub placeholders |

See [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) for deploy steps and env vars; [AI_PLATFORM_PRODUCT_DISCOVERY.md](./AI_PLATFORM_PRODUCT_DISCOVERY.md) for ACP/UCP discovery.
