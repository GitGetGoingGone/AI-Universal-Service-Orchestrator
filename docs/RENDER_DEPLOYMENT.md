# Deploy to Render

Step-by-step instructions to deploy the AI Universal Service Orchestrator full stack on [Render](https://render.com).

## Prerequisites

- [Render](https://render.com) account
- [Supabase](https://supabase.com) staging project (see [STAGING_SETUP.md](STAGING_SETUP.md) Step 1)
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

## Step 3: Create Web Service (Orchestrator)

1. **New** → **Web Service**
2. Same repo
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `uso-orchestrator` |
| **Root Directory** | *(empty)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `cd services/orchestrator-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

4. **Environment** (use URLs from Steps 1–2):

| Key | Value |
|-----|-------|
| `INTENT_SERVICE_URL` | `https://uso-intent.onrender.com` |
| `DISCOVERY_SERVICE_URL` | `https://uso-discovery.onrender.com` |
| `DURABLE_ORCHESTRATOR_URL` | `https://your-durable.azurewebsites.net` *(or leave default)* |
| `AZURE_OPENAI_ENDPOINT` | *(optional)* For agentic planner |
| `AZURE_OPENAI_API_KEY` | *(optional)* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4o` |
| `ENVIRONMENT` | `staging` |

5. Create and note the URL.

---

## Step 4: Create Web Service (Webhook)

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

## Step 5: Update Orchestrator with Webhook URL

After Webhook is deployed:

1. Open **uso-orchestrator** service
2. **Environment** → Edit `WEBHOOK_SERVICE_URL` (if used by Durable Functions)
3. Durable Functions should use `WEBHOOK_SERVICE_URL` in Azure; set it to `https://uso-webhook.onrender.com`

---

## Step 6: Verify Deployment

```bash
# Replace with your Render URLs
DISCOVERY="https://uso-discovery.onrender.com"
INTENT="https://uso-intent.onrender.com"
ORCHESTRATOR="https://uso-orchestrator.onrender.com"
WEBHOOK="https://uso-webhook.onrender.com"

# Health checks
curl $DISCOVERY/health
curl $INTENT/health
curl $ORCHESTRATOR/health
curl $WEBHOOK/health

# Chat flow (main E2E)
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

### Port

- Render sets `$PORT`; the start command uses it
- Do not hardcode port 8000

### Root Directory

- Leave **Root Directory** empty so the build uses the repo root
- Services import `packages/shared` from the root

### Auto-Deploy

- Render deploys on push to the connected branch (default: `main`)
- Disable in **Settings** → **Build & Deploy** if needed

---

## Quick Reference: Start Commands

| Service | Start Command |
|---------|---------------|
| Discovery | `cd services/discovery-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Intent | `cd services/intent-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Orchestrator | `cd services/orchestrator-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Webhook | `cd services/webhook-service && uvicorn main:app --host 0.0.0.0 --port $PORT` |

All use: **Build Command** = `pip install -r requirements.txt`
