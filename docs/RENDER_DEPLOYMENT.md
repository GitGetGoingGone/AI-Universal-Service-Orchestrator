# Deploy to Render

Step-by-step instructions to deploy the AI Universal Service Orchestrator full stack on [Render](https://render.com).

## Prerequisites

- [Render](https://render.com) account
- [Supabase](https://supabase.com) staging project (see [STAGING_SETUP.md](STAGING_SETUP.md) Step 1)
- [Azure Storage](https://portal.azure.com) account (for Durable Orchestrator state)
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

4. **Environment** (use URLs from Steps 1–3):

| Key | Value |
|-----|-------|
| `INTENT_SERVICE_URL` | `https://uso-intent.onrender.com` |
| `DISCOVERY_SERVICE_URL` | `https://uso-discovery.onrender.com` |
| `DURABLE_ORCHESTRATOR_URL` | `https://uso-durable.onrender.com` |
| `WEBHOOK_SERVICE_URL` | `https://uso-webhook.onrender.com` *(add after Step 5)* |
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
| `CHATGPT_WEBHOOK_URL` | *(optional)* |
| `GEMINI_WEBHOOK_URL` | *(optional)* |
| `TWILIO_ACCOUNT_SID` | *(optional)* For WhatsApp |
| `TWILIO_AUTH_TOKEN` | *(optional)* |
| `TWILIO_WHATSAPP_NUMBER` | *(optional)* |

5. Create and note the URL.

---

## Step 6: Update Orchestrator and Durable with Webhook URL

After Webhook is deployed:

1. **uso-orchestrator** → Environment → set `WEBHOOK_SERVICE_URL` = `https://uso-webhook.onrender.com` (if not already set)
2. **uso-durable** → Environment → set `WEBHOOK_SERVICE_URL` = `https://uso-webhook.onrender.com`

---

## Step 7: Verify Deployment

```bash
# Replace with your Render URLs
DISCOVERY="https://uso-discovery.onrender.com"
INTENT="https://uso-intent.onrender.com"
DURABLE="https://uso-durable.onrender.com"
ORCHESTRATOR="https://uso-orchestrator.onrender.com"
WEBHOOK="https://uso-webhook.onrender.com"

# Health checks
curl $DISCOVERY/health
curl $INTENT/health
curl $ORCHESTRATOR/health
curl $WEBHOOK/health
# Durable: Azure Functions uses /api/ prefix
curl "$DURABLE/api/orchestrators/base_orchestrator" -X POST -H "Content-Type: application/json" -d '{}'

# Chat flow (main E2E)
# Tip: On free tier, warm up Discovery and Intent first (curl their /health) to avoid cold-start timeouts
curl -X POST $ORCHESTRATOR/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "find cakes"}'

# Webhook push
curl -X POST $WEBHOOK/api/v1/webhooks/chat/chatgpt/test-123 \
  -H "Content-Type: application/json" \
  -d '{"narrative": "Test update"}'
```

---

## Render-Specific Notes

### Free Tier

- Services spin down after ~15 minutes of inactivity
- First request after spin-down can take 30–60 seconds
- Free tier has limited hours per month
- **Chat flow**: If you get "All connection attempts failed", warm up Discovery and Intent first: `curl $DISCOVERY/health && curl $INTENT/health`, then retry the chat. The orchestrator uses a 60s timeout to tolerate cold starts.

### Port

- Render sets `$PORT`; the start command uses it
- Do not hardcode port 8000

### Root Directory

- **Python services**: Leave **Root Directory** empty so the build uses the repo root (services import `packages/shared`)
- **Durable Orchestrator**: Set **Root Directory** to `functions/durable-orchestrator` (Docker build context)

### Auto-Deploy

- Render deploys on push to the connected branch (default: `main`)
- Disable in **Settings** → **Build & Deploy** if needed

---

## Quick Reference: Start Commands

| Service | Type | Start / Build |
|---------|------|---------------|
| Discovery | Python | Build: `pip install -r requirements.txt` · Start: `cd services/discovery-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Intent | Python | Same build · Start: `cd services/intent-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Durable Orchestrator | Docker | Root: `functions/durable-orchestrator` · No Start Command (image starts automatically) |
| Orchestrator | Python | Same build · Start: `cd services/orchestrator-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Webhook | Python | Same build · Start: `cd services/webhook-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
