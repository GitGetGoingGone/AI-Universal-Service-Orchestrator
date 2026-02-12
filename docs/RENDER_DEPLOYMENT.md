# Deploy to Render

Step-by-step instructions to deploy the AI Universal Service Orchestrator full stack on [Render](https://render.com).

## Prerequisites

- [Render](https://render.com) account
- [Supabase](https://supabase.com) staging project (see [STAGING_SETUP.md](STAGING_SETUP.md) Step 1)
- [Azure Storage](https://portal.azure.com) account (for Durable Orchestrator state)
- [Stripe](https://stripe.com) account (for Payment service; optional for core chat flow)
- GitHub repo connected to Render

---

## Step 0: Create Environment Group (shared variables)

Create one **Environment Group** so you don’t repeat the same variables on every service. [Render Environment Groups](https://docs.render.com/configure-environment-variables#environment-groups) let you share a collection of variables across multiple services; a change in the group updates all linked services.

1. In [Render Dashboard](https://dashboard.render.com) → **Environment Groups** (left pane) → **+ New Environment Group**
2. **Group name:** `uso-shared` (or `uso-staging`)
3. Add these variables:

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SECRET_KEY` | Supabase service role / secret key |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase anon / publishable key |
| `ENVIRONMENT` | `staging` |
| `LOG_LEVEL` | `INFO` |

4. Click **Create Environment Group**.  
   **Tip:** If you have a local `.env` with these keys, use **Add from .env** to bulk-add.

**Optional – scope to project environment:** If you use [Render Projects](https://docs.render.com/docs/projects) to organize services by environment (staging vs production), you can scope this group to a single environment (Manage → Move group) so it can’t be linked to services in other environments.

In the steps below, each service will **link this group** and add only its **service-specific** variables. Service-specific vars always override group vars when both define the same key.

---

## Step 1: Create a Render Web Service (Discovery)

1. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Web Service**
2. Connect your GitHub repository
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-discovery` (or `uso-discovery-staging`) |
| **Region** | Choose closest to your users |
| **Root Directory** | *(leave empty – deploy from repo root)* |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `cd services/discovery-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. **Environment**:
   - Under **Linked Environment Groups**, select `uso-shared` → **Link**
   - Add service-specific vars (for UCP well-known and ACP feed URLs):

| Key | Value |
|-----|-------|
| `DISCOVERY_PUBLIC_URL` | `https://uso-discovery.onrender.com` *(same as Render URL; for UCP/Gemini discovery)* |

5. Click **Create Web Service**. Note the URL (e.g. `https://uso-discovery.onrender.com`).

---

## Step 2: Create Web Service (Intent)

1. **New** → **Web Service**
2. Connect the same GitHub repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-intent` |
| **Root Directory** | *(empty)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `cd services/intent-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. **Environment**:
   - Under **Linked Environment Groups**, select `uso-shared` → **Link**
   - Add service-specific vars (optional for OpenAI):

| Key | Value |
|-----|-------|
| `AZURE_OPENAI_ENDPOINT` | *(optional)* Azure OpenAI endpoint |
| `AZURE_OPENAI_API_KEY` | *(optional)* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4o` |

5. Create and note the URL.

---

## Step 3: Create Docker Web Service (Durable Orchestrator)

The Durable Orchestrator runs as an Azure Functions app in a Docker container. It requires **Azure Storage** for orchestration state.

### 3.1 Create Azure Storage account (if needed)

1. Go to [Azure Portal](https://portal.azure.com) → **Storage accounts** → **Create**
2. Create a storage account (any region; free tier available)
3. **Access keys** → Copy **Connection string** (key1)

### 3.2 Create Render Docker service

1. **New** → **Web Service**
2. Connect the same GitHub repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-durable` |
| **Region** | Same as other services |
| **Environment** / **Language** | **Docker** |
| **Root Directory** | `functions/durable-orchestrator` |
| **Start Command** | *(leave empty – the image CMD starts the host)* |

**Important:** If you set a custom Start Command earlier, **remove it** so the image uses its default CMD. If Render requires a Start Command, use: `func host start`

**Dockerfile Path:** When Root Directory is `functions/durable-orchestrator`, the Dockerfile is at the root of that folder. Render usually auto-detects it. If you see a **Dockerfile Path** field (sometimes under **Advanced** or **Build & Deploy**), leave it empty or set to `Dockerfile`.

4. **Environment**:

| Key | Value |
|-----|-------|
| `AzureWebJobsStorage` | Azure Storage connection string |
| `FUNCTIONS_WORKER_RUNTIME` | `python` |
| `WEBHOOK_SERVICE_URL` | `https://uso-webhook.onrender.com` *(add after Step 5)* |

5. Create and note the URL (e.g. `https://uso-durable.onrender.com`).

**Note:** The Dockerfile uses `$PORT` so the Azure Functions host listens on Render’s port. No extra config needed.

---

## Step 4: Create Web Service (Orchestrator)

1. **New** → **Web Service**
2. Same repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-orchestrator` |
| **Root Directory** | *(empty)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `cd services/orchestrator-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. **Environment**:
   - Under **Linked Environment Groups**, select `uso-shared` → **Link**
   - Add service-specific vars (use URLs from Steps 1–5 and 6a–6d):

| Key | Value |
|-----|-------|
| `INTENT_SERVICE_URL` | `https://uso-intent.onrender.com` |
| `DISCOVERY_SERVICE_URL` | `https://uso-discovery.onrender.com` |
| `DURABLE_ORCHESTRATOR_URL` | `https://uso-durable.onrender.com` |
| `WEBHOOK_SERVICE_URL` | `https://uso-webhook.onrender.com` *(add after Step 5)* |
| `PAYMENT_SERVICE_URL` | `https://uso-payment.onrender.com` *(add after Step 6c)* |
| `OMNICHANNEL_BROKER_URL` | `https://uso-omnichannel-broker.onrender.com` *(add after Step 6b)* |
| `RE_SOURCING_SERVICE_URL` | `https://uso-resourcing.onrender.com` *(add after Step 6c)* |
| `HYBRID_RESPONSE_SERVICE_URL` | `https://uso-hybrid-response.onrender.com` *(for classify-support; add after Step 6e)* |
| `REVERSE_LOGISTICS_SERVICE_URL` | `https://uso-reverse-logistics.onrender.com` *(for returns; optional)* |
| `SUPABASE_SERVICE_KEY` | Same as `SUPABASE_SECRET_KEY` *(for Link Account; alias)* |
| `GOOGLE_OAUTH_CLIENT_ID` | *(optional)* For Link Account with Google; from Google Cloud Console |
| `AZURE_OPENAI_ENDPOINT` | *(optional)* For agentic planner |
| `AZURE_OPENAI_API_KEY` | *(optional)* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4o` |

5. Create and note the URL.

---

## Step 5: Create Web Service (Webhook)

1. **New** → **Web Service**
2. Same repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-webhook` |
| **Root Directory** | *(empty)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `cd services/webhook-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. **Environment**:
   - Under **Linked Environment Groups**, select `uso-shared` → **Link**
   - Add service-specific vars (optional):

| Key | Value |
|-----|-------|
| `CHATGPT_WEBHOOK_URL` | *(optional)* If unset, push to ChatGPT returns 503 (no stub). |
| `GEMINI_WEBHOOK_URL` | *(optional)* If unset, push to Gemini returns 503. |
| `TWILIO_ACCOUNT_SID` | *(optional)* For WhatsApp push |
| `TWILIO_AUTH_TOKEN` | *(optional)* |
| `TWILIO_WHATSAPP_NUMBER` | *(optional)* |

5. Create and note the URL.

---

## Step 6: Create Full Implementation Services (Omnichannel Broker, Re-Sourcing, Payment)

Deploy these services for the full production flow (no simulator).

**Note:** Partner Portal is now a Next.js app deployed on **Vercel** (see `apps/portal`). It is not deployed on Render.

### Step 6a: Omnichannel Broker

1. **New** → **Web Service**
2. Same repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-omnichannel-broker` |
| **Root Directory** | *(empty)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `cd services/omnichannel-broker-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. **Environment**:
   - Under **Linked Environment Groups**, select `uso-shared` → **Link**
   - Add service-specific vars:

| Key | Value |
|-----|-------|
| `RE_SOURCING_SERVICE_URL` | `https://uso-resourcing.onrender.com` *(add after Step 6c)* |

5. Create and note the URL.

### Step 6b: Re-Sourcing Service

1. **New** → **Web Service**
2. Same repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-resourcing` |
| **Root Directory** | *(empty)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `cd services/re-sourcing-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. **Environment**:
   - Under **Linked Environment Groups**, select `uso-shared` → **Link**
   - Add service-specific vars:

| Key | Value |
|-----|-------|
| `DISCOVERY_SERVICE_URL` | `https://uso-discovery.onrender.com` |

5. Create and note the URL.

### Step 6c: Payment Service

1. **New** → **Web Service**
2. Same repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-payment` |
| **Root Directory** | *(empty)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `cd services/payment-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. **Environment**:
   - Under **Linked Environment Groups**, select `uso-shared` → **Link**
   - Add service-specific vars:

| Key | Value |
|-----|-------|
| `STRIPE_SECRET_KEY` | Stripe secret key (sk_test_... or sk_live_...) – from Dashboard → API keys |
| `STRIPE_WEBHOOK_SECRET` | *(optional)* For webhook verification – from Stripe Webhooks |

**Note:** Stripe provides **Publishable key** (pk_...) and **Secret key** (sk_...) in Dashboard → API keys. Use the Secret key for `STRIPE_SECRET_KEY`.

**Optional – webhook verification:** To receive and verify Stripe webhook events (payment success/failure), add a webhook endpoint in Stripe Dashboard → Developers → Webhooks with URL `https://uso-payment.onrender.com/webhooks/stripe` and events `payment_intent.succeeded`, `payment_intent.payment_failed`. Stripe then shows a **Signing secret** (whsec_...) for that endpoint – set it as `STRIPE_WEBHOOK_SECRET`. Without it, the service still creates PaymentIntents but will not verify incoming webhook requests.

### Step 6e: Phase 2 Modules (Task Queue, Hub Negotiator, Hybrid Response)

Requires migration `supabase/migrations/20240128100003_task_queue_hub_negotiator_hybrid.sql` (vendor_tasks, rfps, bids, hub_capacity, support_escalations, response_classifications).

**Task Queue (Module 11):**

| Setting | Value |
|---------|-------|
| **Name** | `uso-task-queue` |
| **Start Command** | `cd services/task-queue-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

**Hub Negotiator (Module 10):**

| Setting | Value |
|---------|-------|
| **Name** | `uso-hub-negotiator` |
| **Start Command** | `cd services/hub-negotiator-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

**Hybrid Response (Module 13):**

| Setting | Value |
|---------|-------|
| **Name** | `uso-hybrid-response` |
| **Start Command** | `cd services/hybrid-response-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

For each: **Root Directory** empty, **Build Command** `pip install -r requirements.txt`, **Environment** → **Linked Environment Groups** → link `uso-shared` (no service-specific vars). Test steps: [TESTING_RENDER_AND_PORTAL.md § 8b](./TESTING_RENDER_AND_PORTAL.md#8b-phase-2-modules-task-queue-hubnegotiator-hybrid-response).

### Step 6f: ChatGPT App (MCP Server)

Node.js MCP server for ChatGPT App Directory. Exposes 12 tools (discover, products, bundles, checkout, manifest, orders, support, returns).

1. **New** → **Web Service**
2. Same repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-chatgpt-app` |
| **Root Directory** | `apps/uso-chatgpt-app` |
| **Runtime** | Node |
| **Build Command** | `npm install && npm run build` |
| **Start Command** | `npm start` |

4. **Environment**:
   - Under **Linked Environment Groups**, select `uso-shared` → **Link**
   - Add service-specific vars:

| Key | Value |
|-----|-------|
| `ORCHESTRATOR_URL` | `https://uso-orchestrator.onrender.com` |
| `DISCOVERY_URL` | `https://uso-discovery.onrender.com` |

5. Create and note the URL (e.g. `https://uso-chatgpt-app.onrender.com`).

**Note:** For ChatGPT App Directory submission, connect this MCP endpoint to ChatGPT via [platform.openai.com](https://platform.openai.com). See [CHATGPT_APP_DIRECTORY_SUBMISSION.md](./CHATGPT_APP_DIRECTORY_SUBMISSION.md).

### Step 6g: Unified Web App (Vercel)

End-user chat app with ChatGPT or Gemini provider switch. Deploy on **Vercel** (like Partner Portal).

1. Go to [Vercel](https://vercel.com) → **Add New** → **Project**
2. Connect your GitHub repo
3. Set **Root Directory** to `apps/uso-unified-chat`
4. Framework: Next.js (auto-detected)
5. Environment variables:

| Key | Value |
|-----|-------|
| `ORCHESTRATOR_URL` | `https://uso-orchestrator.onrender.com` |

6. Deploy. Note the URL (e.g. `https://uso-unified-chat.vercel.app`).

**Test:** Open the URL, select ChatGPT or Gemini provider, send e.g. "Find me flowers".

---

## Gemini (UCP) – Discovery Service

**Gemini UCP** (discovery + checkout) is served by the Discovery service (Step 1). No separate deployment needed.

- **UCP Well-Known:** `GET https://uso-discovery.onrender.com/.well-known/ucp`
- **UCP Catalog:** `GET https://uso-discovery.onrender.com/api/v1/ucp/items?q=flowers`
- **UCP Checkout:** `POST https://uso-discovery.onrender.com/api/v1/ucp/checkout`

Ensure Discovery has `DISCOVERY_PUBLIC_URL` or `PUBLIC_URL` set to its Render URL for correct UCP endpoint URLs in well-known. Test: [CHATGPT_GEMINI_TEST_SCENARIOS.md](./CHATGPT_GEMINI_TEST_SCENARIOS.md).

---

## Step 7: Update Service URLs (after all services deployed)

1. **uso-orchestrator** → Environment → add/update (service-specific vars override group):
   - `WEBHOOK_SERVICE_URL` = `https://uso-webhook.onrender.com`
   - `PAYMENT_SERVICE_URL` = `https://uso-payment.onrender.com` *(required for checkout)*
   - `OMNICHANNEL_BROKER_URL` = `https://uso-omnichannel-broker.onrender.com`
   - `RE_SOURCING_SERVICE_URL` = `https://uso-resourcing.onrender.com`

**Important:** Without `PAYMENT_SERVICE_URL`, createPaymentIntent returns 502 "All connection attempts failed" because the Orchestrator defaults to `http://localhost:8006` which does not exist on Render.

2. **uso-durable** → Environment → `WEBHOOK_SERVICE_URL` = `https://uso-webhook.onrender.com`
3. **uso-omnichannel-broker** → Environment → `RE_SOURCING_SERVICE_URL` = `https://uso-resourcing.onrender.com`

---

## Environment Groups summary

| Source | Variables |
|-------|-----------|
| **`uso-shared` env group** | `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_PUBLISHABLE_KEY`, `ENVIRONMENT`, `LOG_LEVEL` |
| **Service-specific** | Per-service URLs, Stripe keys, Azure keys, webhook URLs, etc. |

Services that link `uso-shared`: Discovery, Intent, Orchestrator, Webhook, Omnichannel Broker, Re-Sourcing, Payment, Task Queue, Hub Negotiator, Hybrid Response. Durable (Docker) does not use the group. When you change a variable in the env group, Render redeploys all linked services (if autodeploy is on).

---

## Step 8: Verify Deployment

**Full testing steps (Chat-First, Link Account, Webhook, Portal):** see [TESTING_RENDER_AND_PORTAL.md](./TESTING_RENDER_AND_PORTAL.md) for curl examples and a checklist.

### Option A: Health and warmup script (recommended)

Run the script to check health and warm up services (avoids cold-start timeouts on free tier):

```bash
# Health checks + warmup (Discovery, Intent, Orchestrator)
./scripts/health-and-warmup.sh

# With chat E2E
./scripts/health-and-warmup.sh --e2e

# With chat E2E and webhook test
./scripts/health-and-warmup.sh --e2e --webhook
```

Override URLs via env if different from defaults:

```bash
DISCOVERY_URL=https://... INTENT_URL=https://... ./scripts/health-and-warmup.sh --e2e
```

The script warms and checks all services (core + full implementation). Full implementation services (Omnichannel Broker, Re-Sourcing, Payment) are optional – if not deployed, they show ✗ [optional] but the script still succeeds. Partner Portal is deployed on Vercel (see `apps/portal`).

### Option B: Manual curl commands

```bash
# Replace with your Render URLs
DISCOVERY="https://uso-discovery.onrender.com"
INTENT="https://uso-intent.onrender.com"
DURABLE="https://uso-durable.onrender.com"
ORCHESTRATOR="https://uso-orchestrator.onrender.com"
WEBHOOK="https://uso-webhook.onrender.com"
OMNICHANNEL="https://uso-omnichannel-broker.onrender.com"
RESOURCING="https://uso-resourcing.onrender.com"
PAYMENT="https://uso-payment.onrender.com"
TASK_QUEUE="https://uso-task-queue.onrender.com"
HUB_NEGOTIATOR="https://uso-hub-negotiator.onrender.com"
HYBRID_RESPONSE="https://uso-hybrid-response.onrender.com"
CHATGPT_APP="https://uso-chatgpt-app.onrender.com"

# Health checks (core)
curl $DISCOVERY/health
curl $INTENT/health
curl $ORCHESTRATOR/health
curl $WEBHOOK/health

# Health checks (full implementation)
curl $OMNICHANNEL/health
curl $RESOURCING/health
curl $PAYMENT/health
curl $TASK_QUEUE/health
curl $HUB_NEGOTIATOR/health
curl $HYBRID_RESPONSE/health

# Durable: Azure Functions uses /api/ prefix
curl "$DURABLE/api/orchestrators/base_orchestrator" -X POST -H "Content-Type: application/json" -d '{}'

# Chat flow (main E2E)
# Tip: On free tier, warm up Discovery and Intent first (curl their /health) to avoid cold-start timeouts
curl -X POST $ORCHESTRATOR/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "find flowers"}'

# Webhook push
curl -X POST $WEBHOOK/api/v1/webhooks/chat/chatgpt/test-123 \
  -H "Content-Type: application/json" \
  -d '{"narrative": "Test update"}'

# Partner Portal: deployed on Vercel (see apps/portal)

# ChatGPT App (MCP) – verify MCP server responds
curl -s $CHATGPT_APP/ -o /dev/null -w "%{http_code}"  # Expect 200 or 405 (GET may not be supported)
# Or: use MCP client to connect and list tools

# Gemini (UCP) – Discovery serves UCP
curl -s $DISCOVERY/.well-known/ucp | jq '.ucp.version'
curl -s "$DISCOVERY/api/v1/ucp/items?q=flowers&limit=2" | jq '.items | length'

# Unified Web App – manual test in browser
# Open https://uso-unified-chat.vercel.app (or your Vercel URL), send "Find me flowers"
```

---

## Render-Specific Notes

### Free Tier

- Services spin down after ~15 minutes of inactivity
- First request after spin-down can take 30–60 seconds
- Free tier has limited hours per month
- **Chat flow**: If you get "All connection attempts failed", run `./scripts/health-and-warmup.sh` first to warm up services, then retry the chat. The orchestrator uses a 60s timeout to tolerate cold starts.

### Port

- Render sets `$PORT`; the start command uses it
- Do not hardcode port 8000

### Root Directory

- **Python services**: Leave **Root Directory** empty so the build uses the repo root (services import `packages/shared`)
- **Durable Orchestrator**: Set **Root Directory** to `functions/durable-orchestrator` (Docker build context)

### Auto-Deploy

- Render deploys on push to the connected branch (default: `main`)
- Disable in **Settings** → **Build & Deploy** if needed

### Troubleshooting: "Payment service error: All connection attempts failed"

The Orchestrator calls the Payment service at `PAYMENT_SERVICE_URL`. If that env var is not set, it defaults to `http://localhost:8006`, which does not exist on Render. **Fix:** Add `PAYMENT_SERVICE_URL=https://uso-payment.onrender.com` to **uso-orchestrator** → Environment, then redeploy.

### Troubleshooting: "d: command not found"

If you see `bash: line 1: d: command not found`, the Start Command is missing `c` from `cd`. Fix: In Render Dashboard → Your Service → **Settings** → **Build & Deploy** → **Start Command**, ensure it begins with `cd` (not `d`). Copy-paste from the Quick Reference table below.

### Troubleshooting: "Port scan timeout reached, no open ports detected"

This means the process never bound to `$PORT` before Render timed out.

Common causes:

1. **App crashes on startup** – Check **Logs** for `ModuleNotFoundError`, `ImportError`, or missing env vars.
2. **Wrong Root Directory** – Must be empty for Python services.
3. **Start command typo** – Ensure `cd` (not `d`) and `uvicorn main:app --host 0.0.0.0 --port $PORT`.
4. **Use `python -m uvicorn`** – If uvicorn isn't on PATH: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Env group not linked** – Ensure `uso-shared` is linked if you use environment groups.

**Optional – gunicorn:** If uvicorn continues to fail, you can switch to gunicorn with uvicorn workers. **Apply across all Python web services** (add `gunicorn>=21.0.0` to requirements.txt and use `gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT` for every service) to keep configuration consistent.

---

## Quick Reference: Start Commands

| Service | Type | Start / Build |
|---------|------|---------------|
| Discovery | Python | Build: `pip install -r requirements.txt` · Start: `cd services/discovery-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Intent | Python | Same build · Start: `cd services/intent-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Durable Orchestrator | Docker | Root: `functions/durable-orchestrator` · No Start Command (image starts automatically) |
| Orchestrator | Python | Same build · Start: `cd services/orchestrator-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Webhook | Python | Same build · Start: `cd services/webhook-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Omnichannel Broker | Python | Same build · Start: `cd services/omnichannel-broker-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Re-Sourcing | Python | Same build · Start: `cd services/re-sourcing-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Payment | Python | Same build · Start: `cd services/payment-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Task Queue | Python | Same build · Start: `cd services/task-queue-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Hub Negotiator | Python | Same build · Start: `cd services/hub-negotiator-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Hybrid Response | Python | Same build · Start: `cd services/hybrid-response-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| ChatGPT App (MCP) | Node | Root: `apps/uso-chatgpt-app` · Build: `npm install && npm run build` · Start: `npm start` |

---

## Partner Portal (Vercel)

The Partner Portal is a Next.js app and is deployed on **Vercel**, not Render.

### Deploy to Vercel

1. Go to [Vercel](https://vercel.com) → **Add New** → **Project**
2. Connect your GitHub repo
3. Set **Root Directory** to `apps/portal`
4. Framework: Next.js (auto-detected)
5. Environment variables:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk publishable key |
| `CLERK_SECRET_KEY` | Clerk secret key |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |

6. Deploy

See `apps/portal/README.md` for local setup and design tokens.

---

## Unified Web App (Vercel)

The Unified Web App (`apps/uso-unified-chat`) is a Next.js chat app with ChatGPT or Gemini provider switch. Deploy on **Vercel** (see Step 6g above).

| Key | Value |
|-----|-------|
| `ORCHESTRATOR_URL` | `https://uso-orchestrator.onrender.com` |

See `apps/uso-unified-chat/README.md` for local setup. Full test prompts: [CHATGPT_GEMINI_TEST_SCENARIOS.md](./CHATGPT_GEMINI_TEST_SCENARIOS.md).
