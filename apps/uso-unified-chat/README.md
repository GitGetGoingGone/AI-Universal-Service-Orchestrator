# USO Unified Chat

End-user chat app with ChatGPT or Gemini provider switch. Both call the orchestrator backend.

## Features

- Provider selector: ChatGPT or Gemini (backend uses orchestrator)
- Chat UI: message list, input
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
