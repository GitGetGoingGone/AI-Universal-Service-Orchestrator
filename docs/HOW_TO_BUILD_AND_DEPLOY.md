# How to Build and Deploy

This guide covers building and running the **AI Universal Service Orchestrator** stack locally and deploying it (e.g. to Render). It includes the **Distributed Business Agent (A2A)** Gateway options: registry, broadcast discovery, ID masking, and unified UCP manifest.

---

## Prerequisites

- **Python 3.11+** (recommend 3.11.x; repo may specify in `.python-version`)
- **Git**
- **Supabase** project (for database; [supabase.com](https://supabase.com))
- **Optional:** Azure Storage (for Durable Orchestrator), Stripe (for payments), Render account (for deploy)

---

## Repository layout

```
AI Universal Service Orchestrator/
├── .env                          # Local env (create from .env.example; do not commit)
├── requirements.txt              # Root Python deps (shared + services)
├── packages/
│   └── shared/                   # Shared libs (gateway_signature, llm_provider, ucp_public_product, etc.)
├── services/
│   ├── discovery-service/       # Scout Engine, UCP catalog, JSON-RPC /api/v1/ucp/rpc
│   ├── intent-service/          # Intent resolution (LLM/heuristics)
│   ├── orchestrator-service/     # Chat, Gateway /.well-known/ucp, broadcast discovery
│   └── webhook-service/         # Webhook push (ChatGPT, Gemini)
├── functions/
│   └── durable-orchestrator/    # Azure Durable Functions (optional)
└── supabase/
    └── migrations/              # DB schema (run via Supabase CLI or Dashboard)
```

---

## 1. Clone and Python setup

```bash
git clone <repo-url>
cd "AI Universal Service Orchestrator"

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Ensure `packages/shared` is importable. From repo root, services run with root as cwd (e.g. `cd services/discovery-service && uvicorn main:app`); the root is typically on `PYTHONPATH` or each service adds the repo root to `sys.path` (see each `main.py`). If you see import errors for `packages.shared`, set:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## 2. Environment variables

Copy the example env and fill in at least Supabase and service URLs:

```bash
cp .env.example .env
# Edit .env with your values
```

**Minimum for local run:**

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` or `SUPABASE_SECRET_KEY` | Service role key |
| `DISCOVERY_SERVICE_URL` | Discovery base URL (e.g. `http://localhost:8000`) |
| `INTENT_SERVICE_URL` | Intent base URL (e.g. `http://localhost:8001`) |

**Orchestrator** (used by chat and Gateway):

| Variable | Description |
|----------|-------------|
| `ORCHESTRATOR_SERVICE_URL` or `ORCHESTRATOR_BASE_URL` | Orchestrator base (e.g. `http://localhost:8002`) |
| `GATEWAY_PUBLIC_URL` | Public URL for `/.well-known/ucp` (e.g. `http://localhost:8002` locally) |

**Distributed A2A / Gateway (optional):**

| Variable | Description |
|----------|-------------|
| `GATEWAY_INTERNAL_SECRET` | Shared secret for X-Gateway-Signature (Orchestrator → Discovery) |
| `ID_MASKING_ENABLED` | Set `true` to mask product ids in broadcast (uso_*); requires Supabase for Orchestrator |
| `ID_MASKING_TTL_HOURS` | TTL in hours for masked id mappings (default 24) |

**Discovery** (when using Gateway handshake):

| Variable | Description |
|----------|-------------|
| `GATEWAY_INTERNAL_SECRET` | Same as Orchestrator (verification) |
| `GATEWAY_SIGNATURE_REQUIRED` or UCP-only middleware | Middleware requires signature on `/api/v1/ucp/*` when secret set |
| `ID_MASKING_ENABLED` | Discovery-side masking (optional if masking at Orchestrator) |

**LLM (Orchestrator planner):**

| Variable | Description |
|----------|-------------|
| `OSS_ENDPOINT`, `OSS_API_KEY`, `OSS_MODEL` | Primary LLM (OpenAI-compatible) |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Fallback LLM |
| `LLM_TIMEOUT_SEC`, `LLM_MAX_RETRIES` | Optional |

Full reference: [docs/ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) (if present) or see `.env.example` and service `config.py` files.

---

## 3. Database (Supabase)

1. Create a Supabase project and get **Project URL** and **service_role key**.
2. Apply migrations (Supabase Dashboard SQL or CLI):

   ```bash
   supabase link --project-ref <your-ref>
   supabase db push
   ```

   Or run the SQL in `supabase/migrations/` in order (by filename).

3. **A2A-related migrations** (if not already applied):
   - `internal_agent_registry` — registry for broadcast discovery
   - `id_masking_map` — ID masking (and optional `agent_slug`, `expires_at` migration)
   - `match_products_v2` — semantic search RPC used by Discovery

4. Seed data (optional): run any seed script or insert test products/partners so discover returns results.

---

## 4. Run services locally

Use **three terminals** (or more if you add Webhook / Durable).

**Terminal 1 – Discovery**

```bash
cd services/discovery-service && uvicorn main:app --reload --port 8000
```

**Terminal 2 – Intent**

```bash
cd services/intent-service && uvicorn main:app --reload --port 8001
```

**Terminal 3 – Orchestrator**

```bash
cd services/orchestrator-service && uvicorn main:app --reload --port 8002
```

Ensure `.env` is at repo root and that root is on `PYTHONPATH` if your run fails on `packages.shared` imports.

---

## 5. Verify local stack

```bash
# Health
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# Discovery
curl "http://localhost:8000/api/v1/discover?intent=flowers"

# Intent
curl -X POST http://localhost:8001/api/v1/resolve \
  -H "Content-Type: application/json" \
  -d '{"text":"I want to send flowers"}'

# Chat (Orchestrator)
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"I want to send flowers to my mom"}'

# Gateway UCP manifest (Orchestrator)
curl http://localhost:8002/.well-known/ucp
```

---

## 6. Distributed A2A (optional)

- **Registry:** Populate `internal_agent_registry` (base_url, display_name, capability, enabled). Orchestrator uses it for `get_agents(capability="discovery")` and `get_capabilities()` for `/.well-known/ucp`. If the table is empty, Orchestrator falls back to a single agent from `DISCOVERY_SERVICE_URL` with slug `discovery`.
- **Broadcast discovery:** Chat uses `discover_products_broadcast`; with multiple registry agents it fans out JSON-RPC `discovery/search` and merges results.
- **ID masking:** Set `ID_MASKING_ENABLED=true` on Orchestrator; product ids in broadcast responses become `uso_{agent_slug}_{short_id}` and are stored in `id_masking_map` with TTL. Discovery resolves them at add-to-bundle and checkout.
- **Gateway signature:** Set `GATEWAY_INTERNAL_SECRET` on both Orchestrator and Discovery; Orchestrator adds `X-Gateway-Signature` to Discovery calls and to Gateway→Discovery proxy requests; Discovery middleware can require it on `/api/v1/ucp/*`.

---

## 7. Deploy (e.g. Render)

For step-by-step deploy to **Render**, use:

- **[docs/RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)** — Create Web Services for Discovery, Intent, Orchestrator, Webhook; optional Docker service for Durable Orchestrator; Environment Groups; service URLs and secrets.

Summary:

1. Create an **Environment Group** with `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `ENVIRONMENT`, etc.
2. Create **Web Services** for Discovery, Intent, Orchestrator (and Webhook if needed) from the same repo; link the group; set **Build** to `pip install -r requirements.txt` and **Start** to the appropriate `cd services/<service> && uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. Set **service-specific** env vars (e.g. `DISCOVERY_PUBLIC_URL`, `INTENT_SERVICE_URL`, `DISCOVERY_SERVICE_URL`, `GATEWAY_PUBLIC_URL`, `GATEWAY_INTERNAL_SECRET`).
4. Apply **migrations** to your Supabase project (same as local).
5. For **A2A**, ensure Orchestrator has `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` for registry and `id_masking_map`; set `GATEWAY_PUBLIC_URL` to the public Orchestrator URL.

---

## 8. Build checklist (summary)

| Step | Action |
|------|--------|
| 1 | Clone repo, create venv, `pip install -r requirements.txt` |
| 2 | Copy `.env.example` → `.env`, set Supabase and service URLs |
| 3 | Apply Supabase migrations (and A2A migrations if using Gateway/registry/masking) |
| 4 | Run Discovery (8000), Intent (8001), Orchestrator (8002) |
| 5 | Hit `/health` and `/api/v1/chat` (and `/.well-known/ucp` if using Gateway) |
| 6 | Deploy: follow RENDER_DEPLOYMENT.md; set env and run migrations on target DB |

For **implementation status** of the Distributed Business Agent (A2A) refactor (JSON-RPC, broadcast, ID masking, unified manifest), see **[docs/implementation-status-distributed-business-agent-a2a.md](implementation-status-distributed-business-agent-a2a.md)**.
