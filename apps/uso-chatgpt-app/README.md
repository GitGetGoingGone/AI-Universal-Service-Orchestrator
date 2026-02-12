# USO ChatGPT App (MCP Server)

MCP server for ChatGPT App Directory with 12 tools for AI Universal Service Orchestrator.

## Tools

| Tool | Description |
|------|-------------|
| `discover_products` | Search products by intent/query |
| `get_product_details` | Get product by ID |
| `get_bundle_details` | Get bundle by ID |
| `add_to_bundle` | Add product to bundle |
| `remove_from_bundle` | Remove item from bundle |
| `proceed_to_checkout` | Start checkout with bundle |
| `create_payment_intent` | Create Stripe payment intent for order |
| `request_change` | Request order change; notifies partner |
| `get_manifest` | Get platform capabilities |
| `track_order` | Get order status |
| `classify_support` | Route support (AI vs human) |
| `create_return` | Create return request |

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 3010 | Server port |
| `ORCHESTRATOR_URL` | http://localhost:8002 | Orchestrator service URL |
| `DISCOVERY_URL` | http://localhost:8000 | Discovery service URL |

## Run

```bash
npm install
npm run build
npm start
# or: npm run dev
```

## Deploy

Deploy to Render, Fly.io, or similar. Set `ORCHESTRATOR_URL` and `DISCOVERY_URL` to your staging/production URLs.

## ChatGPT App Directory

Submit via [platform.openai.com](https://platform.openai.com) Apps SDK. Connect this MCP server endpoint.
