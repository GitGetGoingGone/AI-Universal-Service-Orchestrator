# Assistant UI Chat

Chat UI built on **[assistant-ui](https://www.assistant-ui.com)** (`@assistant-ui/react` + `@assistant-ui/react-ai-sdk`). Connects to the USO Gateway (orchestrator) via an adapter that converts Gateway SSE stream into the Vercel AI SDK UI message stream.

## Setup

### 1. Install

From repo root (or from this directory):

```bash
cd apps/assistant-ui-chat
pnpm install
# or
npm install
```

### 2. Environment

Copy the example env and set the Gateway URL:

```bash
cp .env.example .env
# Edit .env:
# NEXT_PUBLIC_GATEWAY_URL=http://localhost:8002          # local
# NEXT_PUBLIC_GATEWAY_URL=https://uso-orchestrator.onrender.com   # staging
```

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_GATEWAY_URL` | Base URL of the Gateway (orchestrator). Local: `http://localhost:8002`. Staging/prod: your Render orchestrator URL. |

### 3. Run Gateway and Discovery first

The chat app talks to the Gateway; the Gateway talks to Discovery and other services. **Start the backend before the chat app.**

From repo root, run (in separate terminals):

```bash
# Terminal 1: Discovery
cd services/discovery-service && uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Orchestrator (Gateway)
cd services/orchestrator-service && uvicorn main:app --host 0.0.0.0 --port 8002
```

Then start the chat app:

```bash
# Terminal 3: Assistant UI Chat
cd apps/assistant-ui-chat
pnpm dev
# or npm run dev
```

Open **http://localhost:3012**. Send a message (e.g. "Find flowers" or "Plan a date night") to test discovery and streaming.

## Modify (custom parts)

All changes are in this app; we do **not** fork or copy assistant-ui source.

- **Custom part renderers** in `components/GatewayPartRenderers.tsx`:
  - `product_list` → product cards with "Add to bundle"
  - `thematic_options` → theme/bundle choice buttons (add_bundle_bulk)
  - `engagement_choice` → CTAs (Add to bundle, Proceed to payment)
  - `experience_session` → progress/debug view
  - `thinking` → inline thinking text
- **Actions** are sent to the Gateway via `contexts/GatewayActionContext.tsx`. The page implements `handleAction` which calls `/api/bundle/add`, `/api/bundle/add-bulk`, `/api/checkout` (these proxy to the Gateway).

## Deploy

- **Vercel:** Add a project, connect this repo, set **Root Directory** to `apps/assistant-ui-chat`. Set `NEXT_PUBLIC_GATEWAY_URL` to your staging or production Gateway URL (e.g. `https://uso-orchestrator.onrender.com`).
- **CI:** Include this app in path-based deploy — when `apps/assistant-ui-chat/**` changes, build and deploy this app.
- **Staging:** Deploy to a staging URL (e.g. `assistant-ui-chat-staging.vercel.app`) with `NEXT_PUBLIC_GATEWAY_URL` pointing at the staging Gateway. Production: same app, env pointing at production Gateway.

## Stack

- **Next.js** 15
- **@assistant-ui/react** + **@assistant-ui/react-ai-sdk** (Vercel AI SDK integration)
- **ai** (Vercel AI SDK) — adapter uses `createUIMessageStream` / `createUIMessageStreamResponse` to turn Gateway SSE into the stream format assistant-ui expects
