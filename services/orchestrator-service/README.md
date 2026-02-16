# Orchestrator Service - Agentic AI + AI Agents Chat Entry Point

Single endpoint for ChatGPT and Gemini. Resolves intent, discovers products, and supports agentic planning.

## Features

- **AI Agents Chat Entry Point**: `POST /api/v1/chat` – single endpoint for AI chat agents
- **Agentic AI**: LLM-based planning (observe → reason → plan → execute → reflect)
- **Intent → Discovery**: Resolves natural language to structured intent, then discovers products
- **Durable Orchestrator client**: Start long-running workflows via Azure Durable Functions
- **Agentic handoff**: Config for SSO 2.0 (Clerk) when user moves from ChatGPT to custom UI

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | Chat – send user message, get intent + products |
| GET | `/api/v1/agentic-consent` | Agentic consent and agency boundaries |
| GET | `/api/v1/agentic-handoff` | Agentic handoff config (Clerk) |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness (Intent + Discovery) |

## Chat Request

```json
{
  "text": "find the best cakes around me",
  "user_id": "optional-uuid",
  "limit": 20
}
```

Query param: `agentic=true` (default) – use LLM planning. Set `agentic=false` for direct flow.

## Response

```json
{
  "data": {
    "intent": { "intent_type": "discover", "search_query": "cakes", ... },
    "products": { "products": [...], "count": 5 }
  },
  "machine_readable": { "@type": "ChatOrchestrationResult", ... },
  "adaptive_card": { "type": "AdaptiveCard", ... },
  "agent_reasoning": ["Resolving intent...", "Fetching products..."],
  "metadata": { "api_version": "v1", "timestamp": "...", "request_id": "..." }
}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `INTENT_SERVICE_URL` | Intent service (default: http://localhost:8001) |
| `DISCOVERY_SERVICE_URL` | Discovery service (default: http://localhost:8000) |
| `DURABLE_ORCHESTRATOR_URL` | Durable Functions (default: http://localhost:7071) |
| `CLERK_PUBLISHABLE_KEY` | For agentic handoff (optional) |
| `CLERK_SECRET_KEY` | For agentic handoff (optional) |

LLM providers are configured via Platform Config UI. When no active provider is set, the agent uses a fallback planner (heuristics).

## Run

```bash
cd services/orchestrator-service
uvicorn main:app --reload --port 8002
```

Requires Intent Service (8001) and Discovery Service (8000) to be running.
