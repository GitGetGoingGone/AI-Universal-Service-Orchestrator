# ChatGPT & Gemini Test Scenarios

Reproducible test prompts for UCP (Gemini), ChatGPT App (MCP), and Unified Web App.

---

## Prerequisites

- Discovery service running (e.g. `http://localhost:8000`)
- Orchestrator service running (e.g. `http://localhost:8002`)
- Products seeded in database (see `supabase/seed.sql`)

---

## 1. UCP (Gemini) – API

Test via `curl` or Postman. Gemini discovers us via `/.well-known/ucp` and calls these APIs.

### 1.1 UCP Well-Known

```bash
curl -s "$DISCOVERY_URL/.well-known/ucp" | jq .
```

Expected: `ucp.version`, `ucp.services`, `rest.schema` pointing to our OpenAPI schema, `rest.endpoint` with `/api/v1/ucp`.

### 1.2 UCP REST Schema (OpenAPI)

```bash
curl -s "$DISCOVERY_URL/api/v1/ucp/rest.openapi.json" | jq '.paths["/items"].get.operationId'
```

Expected: `"searchGifts"`. The schema documents the tool the AI can call: `GET /items?q=<natural_language>` with optional `occasion`, `budget_max`, `recipient_type`.

### 1.3 UCP Catalog (Discovery)

```bash
curl -s "$DISCOVERY_URL/api/v1/ucp/items?q=flowers&limit=3" | jq .
```

Expected: `items` array with `id`, `title`, `price` (cents), optional `image_url`, `seller_name`.

Gift aggregator params (beads/bridge logic):

```bash
curl -s "$DISCOVERY_URL/api/v1/ucp/items?q=flowers&occasion=birthday&recipient_type=her&budget_max=5000&limit=5" | jq .
```

### 1.4 UCP Checkout – Create

```bash
curl -s -X POST "$DISCOVERY_URL/api/v1/ucp/checkout" \
  -H "Content-Type: application/json" \
  -d '{
    "line_items": [
      {"item": {"id": "PRODUCT_UUID", "title": "Roses", "price": 4999}, "quantity": 1}
    ],
    "currency": "USD",
    "payment": {}
  }' | jq .
```

Expected: `id`, `status`, `line_items`, `continue_url` when `requires_escalation`.

### 1.5 Test Prompts (for Gemini AI Mode)

When testing with Gemini AI Mode pointing at our domain:

- "Find me flowers for under $50"
- "What products do you have?"
- "Add roses to my cart and proceed to checkout"

---

## 2. ChatGPT App (MCP Server)

Ensure MCP server is running: `cd apps/uso-chatgpt-app && npm start`

### 2.1 Verify MCP Tools

Connect a ChatGPT client or MCP client to the server URL. List tools and verify the 12 tools are present:

- `discover_products`
- `get_product_details`
- `get_bundle_details`
- `add_to_bundle`
- `remove_from_bundle`
- `proceed_to_checkout`
- `create_payment_intent`
- `request_change`
- `get_manifest`
- `track_order`
- `classify_support`
- `create_return`

### 2.2 Test Prompts (ChatGPT with App)

After connecting ChatGPT to the MCP server:

- "Find me flowers"
- "Get details for product [product_id]"
- "Add product [product_id] to my bundle"
- "What's the status of order [order_id]?"
- "I want to return my order [order_id]"

---

## 3. Unified Web App

Run: `cd apps/uso-unified-chat && npm run dev` → http://localhost:3011

### 3.1 Test Prompts

1. Select **ChatGPT** provider, send: "Find me flowers for under $50"
2. Select **Gemini** provider, send: "I want chocolates"
3. Compare responses; both should return products from orchestrator.

### 3.2 Example Prompts

- "Find me flowers"
- "I want chocolates"
- "What products are available?"
- "Show me gifts under $30"

---

## 4. Orchestrator Auxiliary Endpoints

### 4.1 Manifest

```bash
curl -s "$ORCHESTRATOR_URL/api/v1/manifest" | jq '.platform_name, .action_models | length'
```

### 4.2 Order Status

```bash
curl -s "$ORCHESTRATOR_URL/api/v1/orders/ORDER_UUID/status" | jq .
```

### 4.3 Classify Support

```bash
curl -s -X POST "$ORCHESTRATOR_URL/api/v1/classify-support" \
  -H "Content-Type: application/json" \
  -d '{"conversation_ref": "conv-1", "message_content": "I need help"}' | jq .
```

### 4.4 Create Return

```bash
curl -s -X POST "$ORCHESTRATOR_URL/api/v1/returns" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORDER_UUID", "partner_id": "PARTNER_UUID", "reason": "other"}' | jq .
```

---

## 5. Environment Variables

| Variable | Example | Used By |
|----------|---------|---------|
| `DISCOVERY_URL` | http://localhost:8000 | UCP, catalog |
| `ORCHESTRATOR_URL` | http://localhost:8002 | Chat, auxiliary, MCP client |
| `PORT` | 3010 | MCP server |
| `ORCHESTRATOR_URL` | http://localhost:8002 | Unified Web App |
