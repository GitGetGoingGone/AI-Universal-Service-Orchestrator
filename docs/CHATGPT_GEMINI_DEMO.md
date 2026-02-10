# ChatGPT & Gemini End-to-End Demo – Implementation Priority

This document outlines the **next priority implementation** to run a full end-to-end demo inside ChatGPT and Gemini.

## Current State ✅

- **API**: `POST /api/v1/chat` – Intent → Discovery flow working
- **Adaptive Cards**: Product, Bundle, etc. with platform renderers (ChatGPT, Gemini)
- **Webhook Push**: Push updates to chat threads (`/api/v1/webhooks/chat/{platform}/{thread_id}`)
- **Durable Orchestrator**: Status Narrator can push to webhook
- **Deployment**: All services on Render (Discovery, Intent, Orchestrator, Webhook, Durable)

## Gap: ChatGPT and Gemini Don’t Call Our API Yet

Right now the flow is: **curl → Orchestrator → products**. For the demo we need: **User in ChatGPT/Gemini → ChatGPT/Gemini calls our API → products shown in chat**.

---

## Priority 1: ChatGPT Custom GPT (Actions)

**Goal**: User says “find flowers” in ChatGPT → ChatGPT calls our API → products appear in chat.

### Steps

1. **Create a Custom GPT** (ChatGPT Plus required)
   - Go to [platform.openai.com](https://platform.openai.com) → Create → GPT
   - Name: e.g. “USO Product Discovery”
   - Instructions: “You help users discover products. When the user asks to find or search for something, call the discover_products action. Present results clearly.”

2. **Add Actions**
   - In the GPT config → Configure → Actions → Create new action
   - **Schema**: Paste the contents of `docs/openapi-chatgpt-actions.yaml` (OpenAPI 3.1.0)
   - The **Server URL** is in the schema's `servers` section: `https://uso-orchestrator.onrender.com`
   - If ChatGPT shows a separate "Server" or "Base URL" field, paste: `https://uso-orchestrator.onrender.com`
   - **Authentication**: None (for demo) or API Key if you add auth

**Schema version**: ChatGPT requires `openapi: 3.1.0` or `3.1.1` (not 3.0.0). Use `docs/openapi-chatgpt-actions.yaml`.

**Server URL**: The schema's `servers` section contains the base URL. ChatGPT reads it from there. If there's no separate Server URL field, ensure your schema has `servers: [{ url: "https://uso-orchestrator.onrender.com" }]`. Edit the schema if your orchestrator URL is different.

3. **OpenAPI Schema for ChatGPT Actions**

ChatGPT Actions expect OpenAPI 3.0. Create `docs/openapi-chatgpt-actions.yaml`:

```yaml
openapi: 3.0.0
info:
  title: USO Product Discovery
  version: 1.0.0
servers:
  - url: https://uso-orchestrator.onrender.com
paths:
  /api/v1/chat:
    post:
      operationId: chat
      summary: Discover products from natural language
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [text]
              properties:
                text:
                  type: string
                  description: User message (e.g. "find flowers", "I want cakes")
                user_id:
                  type: string
                  nullable: true
                limit:
                  type: integer
                  default: 20
      responses:
        "200":
          description: Intent and products
```

4. **Response handling**
   - ChatGPT will show the raw JSON by default. To improve UX:
   - Return a short `summary` or `message` field that ChatGPT can read aloud
   - The `adaptive_card` can be used if ChatGPT supports it (experimental)

---

## Priority 2: Thread Mapping (Implemented ✅)

**Goal**: When ChatGPT/Gemini call our API with `thread_id` and `platform`, register the mapping so Durable can push status updates to the same chat.

**Implementation**: When both are provided, the orchestrator calls `POST /api/v1/webhooks/mappings` to upsert into `chat_thread_mappings`. ChatGPT may not expose `thread_id`; include it in the schema for when it becomes available or for Gemini.

### Implementation

1. **Extend chat request body** (`services/orchestrator-service/api/chat.py`):

```python
class ChatRequest(BaseModel):
    text: str = Field(...)
    user_id: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    # For webhook push - pass when calling from ChatGPT/Gemini
    thread_id: Optional[str] = None
    platform: Optional[Literal["chatgpt", "gemini"]] = None
```

2. **Thread mapping**
   - When `thread_id` + `platform` are provided, upsert into `chat_thread_mappings` (user_id can be null for demo)
   - When starting orchestration, pass `platform` and `thread_id` so Status Narrator can push updates

3. **ChatGPT Actions schema**
   - Add `thread_id` and `platform` to the request body in the OpenAPI schema
   - ChatGPT may expose a conversation ID – check their Actions docs for how to pass it

---

## Priority 3: Gemini Extension / Function Calling

**Goal**: User says “find flowers” in Gemini → Gemini calls our API → products appear.

### Option A: Google AI Studio (Gemini API)

1. Use **Gemini with function calling** (Generative AI API)
2. Define a “function” that calls our `/api/v1/chat` endpoint
3. Your app acts as the middle layer: user talks to Gemini → Gemini decides to call your function → your app calls our API → returns to Gemini

### Option B: Gemini Extensions (if available)

1. Check [Google AI Studio](https://aistudio.google.com) for “Extensions” or “Tools”
2. Add a tool that points to `https://uso-orchestrator.onrender.com/api/v1/chat`
3. Configure the tool schema (similar to ChatGPT Actions)

### Option C: Custom Gemini Agent (Vertex AI)

1. Create an agent in Vertex AI
2. Add a “custom tool” that calls our API
3. Use for production; may be overkill for a quick demo

### Gemini Demo Implementation (Option A – runnable script)

A **runnable demo** is provided so you can try the flow locally without AI Studio:

1. **Tool declaration**  
   `docs/gemini-tool-declaration.json` defines the `discover_products` function (maps to our `POST /api/v1/chat`). Use it when configuring Gemini in code or in AI Studio.

2. **Run the demo script**  
   From the repo root:
   ```bash
   pip install google-generativeai httpx   # or: pip install -r requirements.txt
   export GOOGLE_AI_API_KEY=your_gemini_api_key
   export ORCHESTRATOR_URL=https://uso-orchestrator.onrender.com   # optional, this is the default
   python scripts/gemini_demo.py
   ```
   Then type e.g. **“find flowers”** or **“I want birthday cakes”**. Gemini will call the `discover_products` tool; the script calls the orchestrator and prints the summary and product list.

3. **Env vars**
   - `GOOGLE_AI_API_KEY` or `GEMINI_API_KEY` – required ([get key](https://aistudio.google.com/apikey))
   - `ORCHESTRATOR_URL` – optional; defaults to `https://uso-orchestrator.onrender.com`

4. **Using the same tool in your own app**  
   Use the declaration in `docs/gemini-tool-declaration.json` (or the same structure in `scripts/gemini_demo.py`) when you call the Gemini API with function calling. When Gemini returns a `discover_products` call, run `POST $ORCHESTRATOR_URL/api/v1/chat` with `text` (and optional `limit`, `thread_id`, `platform: "gemini"`) and pass the response back to Gemini or show the `summary` to the user.

---

## Priority 4: Human-Friendly Response for Chat UIs

**Goal**: ChatGPT and Gemini show a readable summary, not only raw JSON.

### Implementation

1. **Add `summary` to chat response** (`services/orchestrator-service/api/chat.py`):

```python
# After building result
summary = _build_summary(result)
return {
    "data": result.get("data", {}),
    "summary": summary,  # "Found 1 product: Red Roses Bouquet ($49.99)"
    "machine_readable": ...,
    "adaptive_card": ...,
}
```

2. **`_build_summary` helper**:
   - If products: “Found N product(s): [names and prices]”
   - If no products: “No products found for your search.”
   - If error: “Sorry, I couldn’t complete your request.”

ChatGPT and Gemini will prefer showing `summary` (or a similar field) as the main text.

---

## Priority 5: Webhook Push from Orchestration (Optional for Demo)

**Goal**: When a long-running orchestration updates, push a message into the user’s ChatGPT/Gemini thread.

### Prerequisites

- `thread_id` and `platform` passed from chat (Priority 2)
- Orchestration input includes `platform` and `thread_id`
- Status Narrator activity calls webhook with those values

### Limitation

- **ChatGPT**: No documented “push to thread” API for Custom GPTs. Updates may require polling or a different mechanism.
- **Gemini**: Similar – check if Gemini supports push/notifications.
- **Workaround**: For the demo, focus on the request–response flow. Push can be a follow-up phase.

---

## Recommended Order

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | ChatGPT Custom GPT + Actions | 1–2 hrs | High – demo works in ChatGPT |
| 2 | Add `thread_id` / `platform` to chat | ~30 min | Medium – enables future push |
| 3 | Add `summary` to chat response | ~30 min | High – better UX in chat |
| 4 | Gemini setup (Studio or Extensions) | 1–2 hrs | High – demo works in Gemini |
| 5 | Webhook push from orchestration | 2+ hrs | Medium – depends on platform support |

---

## Quick Start: ChatGPT Demo

1. Create Custom GPT at [platform.openai.com](https://platform.openai.com)
2. Add Action with schema in `docs/openapi-chatgpt-actions.yaml`, server `https://uso-orchestrator.onrender.com`
3. Test: “Find flowers” → ChatGPT should call the API and show the response
4. The `summary` field is already returned for cleaner display

## Quick Start: Gemini Demo

1. Get a Gemini API key at [Google AI Studio](https://aistudio.google.com/apikey)
2. Run the demo script (see **Gemini Demo Implementation** under Priority 3):
   ```bash
   export GOOGLE_AI_API_KEY=your_key
   python scripts/gemini_demo.py
   ```
3. Type “find flowers” or “I want cakes” → Gemini calls the tool, script calls the orchestrator, products and summary are printed
4. Tool declaration for custom apps: `docs/gemini-tool-declaration.json`

---

## Testing on a “public” Gemini with no configuration

**Can I use the public Gemini website (gemini.google.com) to test USO?**  
**No.** The consumer Gemini chat does not let you add custom tools or APIs. You cannot point it at the orchestrator.

**Ways to test without running the custom script:**

| Option | Config required | Who does it | Result |
|--------|------------------|-------------|--------|
| **ChatGPT Custom GPT** | One-time: create GPT, add Action with `docs/openapi-chatgpt-actions.yaml`, server `https://uso-orchestrator.onrender.com` | You (admin) | Anyone opens that GPT and says “find flowers” with no API key or env; ChatGPT calls the orchestrator. |
| **Hosted web app** | One-time: deploy an app (e.g. Next.js/Vercel) that uses Gemini API + `discover_products` and calls the orchestrator; optional backend proxy so users don’t need keys | You (devops) | Users open the app URL and chat; no local setup. |
| **Google AI Studio** | You still run code. AI Studio gives an API key and samples; it does not provide a “chat UI + one custom API URL” with zero code. | You | Use the API from your code (e.g. `scripts/gemini_demo.py`) or a notebook. |

**Recommendation for a “public, no config” demo:** Use the **ChatGPT Custom GPT** path (one-time schema setup, then test in ChatGPT). For a Gemini-like experience with no script, deploy a **hosted chat app** that uses the Gemini API and `docs/gemini-tool-declaration.json`, calling the orchestrator from your backend.

**Making Gemini look up products via UCP (Google Universal Commerce Protocol):** For **native** discovery (Google/Gemini discovers and calls our catalog), we need `/.well-known/ucp` and a UCP catalog API returning UCP Item shape. See [AI_PLATFORM_PRODUCT_DISCOVERY.md](./AI_PLATFORM_PRODUCT_DISCOVERY.md) § 3.1 “How to make Gemini look up products using UCP.”

---

## References

- [ChatGPT Actions](https://platform.openai.com/docs/actions)
- [Gemini Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)
- Orchestrator API: `docs/api/orchestrator-service.openapi.yaml`
- Webhook API: `docs/api/webhook-service.openapi.yaml`
