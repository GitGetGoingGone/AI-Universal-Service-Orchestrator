# Webhook Push Notification Bridge

Pushes status updates to ChatGPT, Gemini, and WhatsApp chat threads. Used by Durable Functions Status Narrator and other services.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/webhooks/chat/{platform}/{thread_id}` | Push update to chat thread |
| POST | `/api/v1/webhooks/push` | Push (alternative, JSON body) |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness (database) |

## Push Request

```bash
curl -X POST http://localhost:8003/api/v1/webhooks/chat/chatgpt/thread-123 \
  -H "Content-Type: application/json" \
  -d '{"narrative": "Order confirmed", "adaptive_card": {"type": "AdaptiveCard", "body": []}}'
```

Platforms: `chatgpt`, `gemini`, `whatsapp` (thread_id = phone number for WhatsApp)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | For webhook_deliveries, chat_thread_mappings |
| `SUPABASE_SECRET_KEY` | Supabase secret key |
| `CHATGPT_WEBHOOK_URL` | Optional: ChatGPT push endpoint base URL |
| `GEMINI_WEBHOOK_URL` | Optional: Gemini push endpoint base URL |
| `TWILIO_ACCOUNT_SID` | Optional: For WhatsApp push |
| `TWILIO_AUTH_TOKEN` | Optional |
| `TWILIO_WHATSAPP_NUMBER` | Optional: e.g. +14155238886 |

When platform URLs are not configured, pushes are logged but not sent (stub mode).

## Run

```bash
cd services/webhook-service
uvicorn main:app --reload --port 8003
```

## Durable Functions Integration

Set `WEBHOOK_SERVICE_URL` in Durable Functions config. The `status_narrator_activity` calls:

```
POST {WEBHOOK_SERVICE_URL}/api/v1/webhooks/chat/{platform}/{thread_id}
```
