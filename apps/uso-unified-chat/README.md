# USO Unified Chat

End-user chat app. Calls the orchestrator backend; LLM provider/model is configured in the admin portal.

## Features

- Chat UI: message list, input, adaptive cards
- Proxies to `POST /api/v1/chat` on orchestrator

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_URL` | http://localhost:8002 | Orchestrator service URL |

## Run

```bash
npm install
npm run dev
# http://localhost:3011
```

## Deploy

Deploy to Vercel. Set `ORCHESTRATOR_URL` to your staging/production orchestrator URL.
