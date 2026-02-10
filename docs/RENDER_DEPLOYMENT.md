# Deploy to Render

Step-by-step instructions to deploy the AI Universal Service Orchestrator full stack on [Render](https://render.com).

## Prerequisites

- [Render](https://render.com) account
- [Supabase](https://supabase.com) staging project (see [STAGING_SETUP.md](STAGING_SETUP.md) Step 1)
- [Azure Storage](https://portal.azure.com) account (for Durable Orchestrator state)
- [Stripe](https://stripe.com) account (for Payment service; optional for core chat flow)
- GitHub repo connected to Render

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

4. **Environment** → Add variables:

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key |
| `SUPABASE_SECRET_KEY` | Supabase secret key |
| `ENVIRONMENT` | `staging` |
| `LOG_LEVEL` | `INFO` |

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

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | Same as Discovery |
| `SUPABASE_SECRET_KEY` | Same as Discovery |
| `AZURE_OPENAI_ENDPOINT` | *(optional)* Azure OpenAI endpoint |
| `AZURE_OPENAI_API_KEY` | *(optional)* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4o` |
| `ENVIRONMENT` | `staging` |

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

4. **Environment** (use URLs from Steps 1–5 and 6a–6d):

| Key | Value |
|-----|-------|
| `INTENT_SERVICE_URL` | `https://uso-intent.onrender.com` |
| `DISCOVERY_SERVICE_URL` | `https://uso-discovery.onrender.com` |
| `DURABLE_ORCHESTRATOR_URL` | `https://uso-durable.onrender.com` |
| `WEBHOOK_SERVICE_URL` | `https://uso-webhook.onrender.com` *(add after Step 5)* |
| `PAYMENT_SERVICE_URL` | `https://uso-payment.onrender.com` *(add after Step 6d)* |
| `OMNICHANNEL_BROKER_URL` | `https://uso-omnichannel-broker.onrender.com` *(add after Step 6b)* |
| `RE_SOURCING_SERVICE_URL` | `https://uso-resourcing.onrender.com` *(add after Step 6c)* |
| `SUPABASE_URL` | Same as Discovery *(required for Link Account)* |
| `SUPABASE_SERVICE_KEY` | Same as `SUPABASE_SECRET_KEY` *(for Link Account)* |
| `GOOGLE_OAUTH_CLIENT_ID` | *(optional)* For Link Account with Google; from Google Cloud Console |
| `AZURE_OPENAI_ENDPOINT` | *(optional)* For agentic planner |
| `AZURE_OPENAI_API_KEY` | *(optional)* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4o` |
| `ENVIRONMENT` | `staging` |

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

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | Same as Discovery |
| `SUPABASE_SECRET_KEY` | Same as Discovery |
| `ENVIRONMENT` | `staging` |
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

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | Same as Discovery |
| `SUPABASE_SECRET_KEY` | Same as Discovery |
| `RE_SOURCING_SERVICE_URL` | `https://uso-resourcing.onrender.com` *(add after Step 6c)* |
| `ENVIRONMENT` | `staging` |

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

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | Same as Discovery |
| `SUPABASE_SECRET_KEY` | Same as Discovery |
| `DISCOVERY_SERVICE_URL` | `https://uso-discovery.onrender.com` |
| `ENVIRONMENT` | `staging` |

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

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | Same as Discovery |
| `SUPABASE_SECRET_KEY` | Same as Discovery |
| `STRIPE_SECRET_KEY` | Stripe secret key (sk_test_... or sk_live_...) – from Dashboard → API keys |
| `ENVIRONMENT` | `staging` |

**Note:** Stripe provides **Publishable key** (pk_...) and **Secret key** (sk_...) in Dashboard → API keys. Use the Secret key for `STRIPE_SECRET_KEY`.

**Optional – webhook verification:** To receive and verify Stripe webhook events (payment success/failure), add a webhook endpoint in Stripe Dashboard → Developers → Webhooks with URL `https://uso-payment.onrender.com/webhooks/stripe` and events `payment_intent.succeeded`, `payment_intent.payment_failed`. Stripe then shows a **Signing secret** (whsec_...) for that endpoint – set it as `STRIPE_WEBHOOK_SECRET`. Without it, the service still creates PaymentIntents but will not verify incoming webhook requests.

---

## Step 7: Update Service URLs (after all services deployed)

1. **uso-orchestrator** → Environment → add/update:
   - `WEBHOOK_SERVICE_URL` = `https://uso-webhook.onrender.com`
   - `PAYMENT_SERVICE_URL` = `https://uso-payment.onrender.com` *(required for checkout)*
   - `OMNICHANNEL_BROKER_URL` = `https://uso-omnichannel-broker.onrender.com`
   - `RE_SOURCING_SERVICE_URL` = `https://uso-resourcing.onrender.com`

**Important:** Without `PAYMENT_SERVICE_URL`, createPaymentIntent returns 502 "All connection attempts failed" because the Orchestrator defaults to `http://localhost:8006` which does not exist on Render.
3. **uso-durable** → Environment → `WEBHOOK_SERVICE_URL` = `https://uso-webhook.onrender.com`
4. **uso-omnichannel-broker** → Environment → `RE_SOURCING_SERVICE_URL` = `https://uso-resourcing.onrender.com`

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

# Health checks (core)
curl $DISCOVERY/health
curl $INTENT/health
curl $ORCHESTRATOR/health
curl $WEBHOOK/health

# Health checks (full implementation)
curl $OMNICHANNEL/health
curl $RESOURCING/health
curl $PAYMENT/health

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
