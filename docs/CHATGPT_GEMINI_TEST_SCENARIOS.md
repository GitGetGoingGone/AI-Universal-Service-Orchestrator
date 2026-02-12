# ChatGPT & Gemini Test Scenarios

Reproducible test prompts for UCP (Gemini), ChatGPT App (MCP), and Unified Web App.

**UCP Schema:** `rest.openapi.json` v2026-01-11 — operationIds: `searchGifts`, `create_checkout`, `get_checkout`, `update_checkout`, `complete_checkout`, `cancel_checkout`.

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

Expected: `ucp.version`, `ucp.services`, `rest.schema` pointing to `{base}/api/v1/ucp/rest.openapi.json`, `rest.endpoint` with UCP base path.

### 1.2 UCP REST Schema (OpenAPI)

```bash
curl -s "$DISCOVERY_URL/api/v1/ucp/rest.openapi.json" | jq '.paths["/items"].get.operationId'
```

Expected: `"searchGifts"`. The schema documents the tool the AI can call: `GET /items?q=<natural_language>` with optional params:

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string (required) | Natural language search query |
| `limit` | integer (1–100, default 20) | Max items to return |
| `partner_id` | string | Filter by vendor |
| `occasion` | enum | `birthday`, `anniversary`, `baby_shower`, `wedding`, `holiday`, `thank_you`, `get_well`, `graduation`, `general` |
| `budget_max` | integer (cents) | Max budget (e.g. 5000 = $50) |
| `recipient_type` | enum | `her`, `him`, `them`, `baby`, `couple`, `family`, `any` |

### 1.3 UCP Catalog (Discovery)

```bash
curl -s "$DISCOVERY_URL/api/v1/ucp/items?q=flowers&limit=3" | jq .
```

Expected: `items` array with UCP Item shape (`id`, `title`, `price` in cents, optional `image_url`, `seller_name`).

Gift aggregator params (align with rest.openapi.json operationId `searchGifts`):

```bash
curl -s "$DISCOVERY_URL/api/v1/ucp/items?q=flowers&occasion=birthday&recipient_type=her&budget_max=5000&limit=5" | jq .
```

### 1.4 UCP Checkout (per rest.openapi.json)

**Create** (`operationId: create_checkout`):

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

Expected: `id`, `status`, `line_items`, `continue_url` when payment required.

**Get** (`operationId: get_checkout`):

```bash
curl -s "$DISCOVERY_URL/api/v1/ucp/checkout/CHECKOUT_ID" | jq .
```

**Update** (`operationId: update_checkout`):

```bash
curl -s -X PUT "$DISCOVERY_URL/api/v1/ucp/checkout/CHECKOUT_ID" \
  -H "Content-Type: application/json" \
  -d '{"line_items": [...], "buyer": {}, "currency": "USD"}' | jq .
```

**Complete** (`operationId: complete_checkout`):

```bash
curl -s -X POST "$DISCOVERY_URL/api/v1/ucp/checkout/CHECKOUT_ID/complete" \
  -H "Content-Type: application/json" \
  -d '{"payment_data": {}, "risk_signals": {}}' | jq .
```

**Cancel** (`operationId: cancel_checkout`):

```bash
curl -s -X POST "$DISCOVERY_URL/api/v1/ucp/checkout/CHECKOUT_ID/cancel" | jq .
```

### 1.5 Test Prompts (for Gemini AI Mode)

When testing with Gemini AI Mode pointing at our domain. Gemini uses `searchGifts` with natural language `q` and optional gift params:

- "Find me flowers for under $50" → `q=flowers for under $50`, `budget_max=5000`
- "What products do you have?" → `q=products` or browse
- "Gifts for mom's birthday under $30" → `q=gifts for mom`, `occasion=birthday`, `budget_max=3000`
- "Baby shower gift for her" → `q=baby shower gift`, `occasion=baby_shower`, `recipient_type=her`
- "Add roses to my cart and proceed to checkout" → `create_checkout` with line item

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
- "Birthday gift for her under $50" (tests `occasion` + `recipient_type` + `budget_max` when using Gemini UCP)

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

## 5. Troubleshooting: Gemini Returns Its Own Products Instead of Ours

**Symptom:** Gemini connects to `/.well-known/ucp` but lists products from its training data (Posh Peanut, Caden Lane, Estella, Nike, Hatch) instead of your catalog. Even when explicitly asked to "Call the searchGifts API", Gemini may claim it did so but still return hallucinated products.

**Cause:** Gemini may **not actually execute** HTTP requests to arbitrary URLs in this context. It can read the manifest and simulate responses, but the products it returns do not come from your API.

**Proof:** Your catalog returns real products like `Red Roses Bouquet` (Flower Shop Demo). If Gemini lists Posh Peanut, Caden Lane, Estella, Nike, or Hatch, it did **not** call your API—those are from Gemini's training data.

**Verification:**
```bash
# Your actual catalog (e.g. Red Roses Bouquet, Flower Shop Demo)
curl -s "https://uso-discovery.onrender.com/api/v1/ucp/items?q=flowers&limit=5" | jq .
curl -s "https://uso-discovery.onrender.com/api/v1/ucp/items?q=products&limit=10" | jq .
```

**How to detect hallucinations:** If Gemini returns Posh Peanut, Caden Lane, Estella, Nike, Hatch, or Hatch Rest+—it did not call your API. Your catalog has different products (e.g. Red Roses Bouquet, Flower Shop Demo).

**Google UCP integration:** Full discovery (Gemini actually calling your APIs) requires [Google UCP merchant registration](https://support.google.com/merchants/contact/ucp_integration_interest). Until approved, Gemini may not execute HTTP requests to your catalog.

**Reliable alternative:** Use the [Unified Web App](http://localhost:3011) with the **Gemini** provider—it proxies to your orchestrator and Discovery, returning your real products. The Unified Web App makes real API calls; Gemini chat in its own UI may not.

---

## 6. Environment Variables

| Variable | Example | Used By |
|----------|---------|---------|
| `DISCOVERY_URL` | https://uso-discovery.onrender.com | UCP, catalog |
| `ORCHESTRATOR_URL` | http://localhost:8002 | Chat, auxiliary, MCP client |
| `PORT` | 3010 | MCP server |
| `ORCHESTRATOR_URL` | http://localhost:8002 | Unified Web App |
