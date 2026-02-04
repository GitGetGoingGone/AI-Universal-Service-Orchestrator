# Staging Environment Setup

Instructions for creating a staging environment so server-based tests and pre-production validation run against a deployed service.

## Overview

| Environment | Purpose |
|-------------|---------|
| **Local** | Development on your machine (`localhost:8000`) |
| **Staging** | Deployed copy for testing, CI, and QA before production |
| **Production** | Live users |

Staging needs:
1. **Database** – Supabase project (separate from production)
2. **Discovery service** – Deployed and reachable via URL
3. **CI secret** – `DISCOVERY_SERVICE_URL` for server tests

---

## Step 1: Supabase Staging Project

Create a dedicated Supabase project for staging (do not reuse production).

### 1.1 Create project

1. Go to [supabase.com](https://supabase.com) → New Project
2. Name it (e.g. `uso-staging`)
3. Choose region (same as production if possible)
4. Set a strong password and save it

### 1.2 Apply migrations

**Option A: Supabase CLI**

```bash
supabase login
supabase link --project-ref <staging-project-ref>
supabase db push
```

Project ref is in the URL: `https://app.supabase.com/project/<project-ref>`

**Option B: Supabase Dashboard**

1. SQL Editor → New Query
2. Run each file in `supabase/migrations/` in order (by filename)
3. Run `supabase/seed.sql` for test data

### 1.3 Get credentials

Project Settings → API:

- `SUPABASE_URL` (Project URL)
- `SUPABASE_PUBLISHABLE_KEY` (sb_publishable_...)
- `SUPABASE_SECRET_KEY` (sb_secret_...)

Save these for Step 3.

---

## Step 2: Deploy Discovery Service

Choose one hosting option. All support Python/FastAPI.

> **Important**: The discovery service imports `packages/shared` from the repo root. Deploy from the **repo root**, not from `services/discovery-service` alone.

### Option A: Railway (simple, free tier)

1. Go to [railway.app](https://railway.app) → New Project
2. Deploy from GitHub: connect repo, use **repo root**
3. Settings:
   - **Root Directory**: (leave empty = repo root)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd services/discovery-service && uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables (Step 3)
5. Deploy → get URL (e.g. `https://discovery-service-xxx.up.railway.app`)

Railway sets `PORT` automatically.

### Option B: Render

1. Go to [render.com](https://render.com) → New → Web Service
2. Connect GitHub repo
3. Settings:
   - **Root Directory**: (leave empty = repo root)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd services/discovery-service && uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables
5. Deploy → get URL (e.g. `https://discovery-service-xxx.onrender.com`)

### Option C: Fly.io

Use the Dockerfile from Option E. From **repo root**:

```bash
fly launch  # follow prompts, choose region, name app e.g. uso-discovery-staging
# When prompted "Dockerfile path", enter: Dockerfile (create it per Option E first)
fly secrets set SUPABASE_URL=... SUPABASE_SECRET_KEY=... SUPABASE_PUBLISHABLE_KEY=...
fly deploy
```

URL: `https://<app-name>.fly.dev`

### Option D: Azure App Service

1. Create App Service (Linux, Python 3.11) via [Azure Portal](https://portal.azure.com) or CLI
2. Deployment: GitHub Actions, ZIP deploy, or local Git (see [Git and Azure CLI](GIT_AZURE_CLI_SETUP.md))
3. Startup command: `cd services/discovery-service && uvicorn main:app --host 0.0.0.0 --port 8000`
4. Configuration → Application settings: add env vars
5. Get URL: `https://<app-name>.azurewebsites.net`

### Option E: Docker + any host

Create `Dockerfile` at **repo root**:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY packages ./packages
COPY services/discovery-service ./services/discovery-service
WORKDIR /app/services/discovery-service
ENV PYTHONPATH=/app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t discovery-service .
docker run -p 8000:8000 -e SUPABASE_URL=... -e SUPABASE_SECRET_KEY=... discovery-service
```

Deploy the image to any host (EC2, DigitalOcean, Cloud Run, ECS, etc.).

---

## Step 3: Environment Variables for Staging

Set these in your hosting platform (Railway, Render, Fly.io, etc.):

| Variable | Value |
|----------|-------|
| `SUPABASE_URL` | Staging Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Staging publishable key |
| `SUPABASE_SECRET_KEY` | Staging secret key |
| `ENVIRONMENT` | `staging` |
| `LOG_LEVEL` | `INFO` |

Optional (add when those modules exist):

- `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` (use Clerk dev instance for staging)
- `API_BASE_URL` – public URL of this service (for links in responses)

---

## Step 4: Verify Staging

1. Open your staging URL in a browser or with curl:

```bash
curl https://your-staging-url/health
curl https://your-staging-url/ready
curl "https://your-staging-url/api/v1/discover?intent=flowers"
```

2. Expect:
   - `/health` → `{"status":"healthy",...}`
   - `/ready` → `{"status":"healthy","dependencies":[...]}`
   - `/discover` → JSON with `data`, `machine_readable`, `adaptive_card`

---

## Step 5: Configure CI (GitHub Actions)

1. GitHub repo → Settings → Secrets and variables → Actions
2. New repository secret:
   - **Name**: `DISCOVERY_SERVICE_URL`
   - **Value**: `https://your-staging-url` (no trailing slash)

3. Server tests will run on push (when discovery service or tests change) and use this URL.

### Manual run with override

Actions → Server Tests → Run workflow → optionally enter a different URL.

---

## Checklist

- [ ] Supabase staging project created
- [ ] Migrations applied to staging DB
- [ ] Seed data applied (optional)
- [ ] Discovery service deployed to Railway/Render/Fly.io/Azure
- [ ] Staging env vars set on host
- [ ] `/health`, `/ready`, `/discover` return expected responses
- [ ] `DISCOVERY_SERVICE_URL` added as GitHub secret
- [ ] Server tests pass: `pytest tests/ -v -m server` (with URL set)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `/ready` returns unhealthy | Check Supabase credentials; DB must be reachable from host |
| 502 Bad Gateway | Service may not be listening on `0.0.0.0` or wrong port |
| CORS errors | Discovery service allows `*`; if frontend has issues, add staging origin |
| Migrations fail | Ensure migrations run in order; check for existing objects |
| Tests fail in CI | Verify `DISCOVERY_SERVICE_URL` secret is set and URL is reachable from GitHub runners |
