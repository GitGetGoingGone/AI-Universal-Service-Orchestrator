# How AI Platforms Detect Our Products and Services

ACP and UCP use **different models** for how products reach the AI. Only ACP is a true “push into their database”; UCP is “expose your API so the platform can call you.” This doc explains both and how we ensure products and services are detected by ChatGPT and Google (AI Mode / Gemini).

---

## 1. Two ways products get in front of AI

| Model | Who calls whom | Where products live | Used by |
|-------|----------------|---------------------|--------|
| **Backend integration** | AI platform calls **our** API (orchestrator → discovery) | Our database | ChatGPT Actions, Gemini with our endpoint |
| **Native platform index** | User search hits the **platform’s** product index or the platform calls **our** UCP API | OpenAI’s index (ACP) or our API (UCP) | ChatGPT Search/Shopping, Google AI Mode |

Today we support **backend integration**: when ChatGPT or Gemini is configured to use our orchestrator (`POST /api/v1/chat`), they call our discovery service and our products are returned. No push to OpenAI or Google is required for that.

For **native** discovery (e.g. user searches in ChatGPT or Google and our products appear), we must either **push a feed (ACP)** or **expose a UCP API (UCP)** as below.

---

## 2. ACP (OpenAI): push feed into ChatGPT’s index

**How it works**

- OpenAI **ingests** merchant product data into **their** systems.
- Merchants **push** a feed via **hosted URL**, **SFTP**, or **file upload**. Formats: **jsonl.gz**, **csv.gz**. Refresh is typically **daily**.
- After ingestion, ChatGPT **search/shopping** uses that index; products are “in their database.”

**How we ensure products are detected**

1. **Register** as a merchant / feed provider at [chatgpt.com/merchants](https://chatgpt.com/merchants) (or the program OpenAI provides).
2. **Build an ACP-compliant feed** from our catalog:
   - Export products from our `products` table (and partner data) into the [Product Feed Spec](https://developers.openai.com/commerce/specs/feed) format.
   - Include all required fields (item_id, title, description, url, image_url, price, availability, brand, seller_*, return_policy, target_countries, store_country, is_eligible_search, is_eligible_checkout, etc.). Use [ACP compliance validation](./ACP_COMPLIANCE.md) before export.
3. **Deliver the feed** using one of OpenAI’s delivery options:
   - **Hosted URL**: Publish a URL that returns the feed (or jsonl.gz/csv.gz). OpenAI fetches on their schedule (e.g. daily).
   - **SFTP / file upload**: If OpenAI supports it, push the file to their endpoint.
4. **Keep the feed fresh**: Update whenever products, prices, or availability change so ChatGPT’s index stays accurate.

**What we need to build**

- **Feed export pipeline**: From our DB → ACP-shaped jsonl.gz (or csv.gz). Fill missing ACP fields from `partners` (seller_name, seller_url, etc.) and `metadata` or new columns (url, brand, return_policy, target_countries, store_country, eligibility flags).
- **Public feed URL** (if using hosted URL): e.g. `GET /api/v1/feeds/acp` or a static job that publishes to a public URL OpenAI can poll.
- **Registration**: Complete OpenAI’s merchant/feed onboarding and point them at our feed URL or use their upload/SFTP flow.

Once the feed is submitted and ingested, **detection is ensured by OpenAI’s indexing**; we don’t control ranking, only that our products are in the pool.

### 2.0 Feed URL and push API (implemented)

**Feed URL**

- **`GET /api/v1/feeds/acp`** — Public ACP feed URL. Returns JSON Lines (one JSON object per line), `Content-Type: application/x-ndjson`. Optional query: **`?partner_id=<id>`** to return only that partner's products. Point OpenAI's hosted-URL delivery at this URL (or at a per-partner URL with `partner_id`).
- Products are joined with partner seller fields (seller_name, seller_url, return_policy, etc.) and filtered to ACP-compliant rows only.

**Push API (on-demand catalog update)**

- **`POST /api/v1/feeds/push`** — Push catalog to ChatGPT and/or Gemini. Body: **`scope`** (`"single"` \| `"all"`), **`product_id`** (required when scope is `"single"`), **`targets`** (`["chatgpt"]` \| `["gemini"]` \| `["chatgpt", "gemini"]`), **`partner_id`** (required for discovery service).
- **ChatGPT**: Builds ACP feed (single product or all for partner), then updates `partners.last_acp_push_at`. Subject to a **15-minute rate limit per partner**: if the partner has already pushed within the last 15 minutes, the API returns **429** with body `{ "error": "rate_limited", "message": "Catalog can be updated again at {ISO time}", "next_allowed_at": "<ISO8601>" }`.
- **Gemini**: Runs UCP validation on the product(s) and returns a summary (e.g. `{ "gemini": "validated", "ucp_compliant": N, "ucp_non_compliant": M }`). No rate limit.
- **`GET /api/v1/feeds/push-status?partner_id=<id>`** — Returns `{ "next_acp_push_allowed_at": "<ISO>" }` (from partner's `last_acp_push_at` + 15 minutes). Used by the partner portal for countdown/disable logic.

**Partner portal**

- In the partner portal, **Settings → Commerce profile** lets partners edit seller fields via **PATCH /api/partners/me**. **Products** hosts all push features: at the top, **Push to AI catalog** with buttons "Push to ChatGPT", "Push to Gemini", "Push to both" (entire catalog). The UI fetches **GET /api/feeds/push-status** and, if `next_acp_push_allowed_at` is in the future, disables the ChatGPT (and "both") button and shows "Next update at {time}". The products table shows **Last pushed** and **Status** (Success/Failed) per product.
- From a product edit page, partners can also use "Push to ChatGPT / Gemini" for that single product (scope=single, product_id=current); that product’s last pushed time and success status are shown and updated after push.

**OpenAI registration** is a manual step: document the feed URL for OpenAI and that they must not pull more than once per 15 minutes if we push on demand (or use their scheduled fetch).

### 2.1 Ensuring merchant on record is the actual merchant (not our platform)

We are an **orchestrator/marketplace**: products belong to **partners** (the actual merchants). When we push an ACP feed, we must ensure each product is attributed to the **partner**, not to our platform.

**In the feed (per product row)**

- **Never** use our platform name or URL as `seller_name` / `seller_url` for products we don’t ourselves sell.
- **Always** set seller fields from the **partner** that owns the product:
  - Join `products` → `partners` (via `products.partner_id`).
  - Set `seller_name` = partner’s public name (e.g. `partners.business_name`, max 70 chars).
  - Set `seller_url` = partner’s site or profile URL (HTTPS).
  - Set `return_policy` (and when checkout-eligible: `seller_privacy_policy`, `seller_tos`) from **partner**-level data, not platform defaults.
- **Product URL** (`url`): Prefer the partner’s product page if they have one; otherwise use our product detail page that **clearly shows** “Sold by {partner.business_name}” so users and the platform see the real merchant.

**Data model**

- Store partner-level seller fields on `partners` (or a related table): e.g. `business_name`, `seller_url`, `return_policy_url`, `privacy_policy_url`, `terms_url`, `store_country`, and optionally `target_countries`. Feed export then reads product + partner and emits one row per product with that partner’s seller_*.
- If a product has no partner (e.g. platform-owned), then and only then use platform as seller.

**Registration model (optional)**

- **Single feed, multi-seller**: We register **once** with OpenAI and submit one feed. Each row has different `seller_name` / `seller_url` per partner. The “merchant account” with OpenAI is us (the platform), but **attribution in the index** is per row, so ChatGPT can show “Sold by Partner A” etc. Confirm with OpenAI that multi-seller feeds are supported.
- **One feed per partner**: Each partner has their **own** merchant registration with OpenAI; we generate a **separate** feed URL or file per partner (e.g. `GET /api/v1/feeds/acp?partner_id=...`) and the partner (or we on their behalf) submits that feed. Then the “merchant on record” at OpenAI is literally the partner. Use this if OpenAI requires one merchant per feed or partners need their own contracts.

**Summary**: Merchant on record = actual merchant is ensured by **sourcing every seller_* and policy field from the partner record** for each product and, if needed, using per-partner feed registration.

### 2.2 Bundling across different products and services

**Bundling is independent of the feed.** The feed is for **discovery and attribution**: it lists **individual products**, each with the correct merchant (partner). It does **not** list “bundles.”

**How bundling still works**

- **Discovery**: User sees products in ChatGPT/Google (from the feed or our UCP catalog). Each product is attributed to its partner.
- **Basket/bundle**: User adds products from **multiple** partners into one bundle via **our** APIs (`POST /api/v1/bundle/add`, etc.). Our orchestrator and discovery service already support cross-partner search and bundle legs; no change needed for that.
- **Checkout**: When the user checks out, **we** create one **order** with multiple **order_items** (or order_legs), each with the appropriate `partner_id`. We handle:
  - Split payments or single payment with internal split by partner.
  - Fulfillment and notifications per partner.
  - Optional partner-facing order APIs or webhooks so each merchant only sees their line items.

So: **feed** = per-product, per-partner attribution so “merchant on record” is correct. **Bundling** = our runtime behavior (bundle + checkout APIs and order/order_items/order_legs by partner). We don’t put bundles in the feed; we keep managing cross-partner bundles and orders in our own layer.

---

## 3. UCP (Google): expose our catalog so the platform can call us

**How it works**

- Google does **not** require us to push a copy of our catalog into “their database.”
- We expose a **UCP-compliant** profile and APIs. The platform **discovers** us (e.g. via `/.well-known/ucp`) and **calls our APIs** when it needs catalog or checkout.
- Products stay on **our** side; detection happens when the platform discovers our domain and calls our **catalog** (and optionally checkout) endpoints.

**How we ensure products are detected**

1. **Publish UCP profile** at `/.well-known/ucp` on a public base URL (e.g. `https://our-domain.com/.well-known/ucp`).
   - Declare capabilities (e.g. catalog search, checkout) and point to our REST or MCP endpoints.
   - See [UCP Specification](https://ucp.dev/specification/overview/) and [Schema Reference](https://ucp.dev/specification/reference/).
2. **Implement catalog (and optionally checkout)** so the platform can:
   - **Search/browse** our products (e.g. catalog search or product list endpoint that returns UCP Item shape: id, title, price in cents, image_url).
   - **Create checkout** with line items (item id, quantity) and complete orders if we support native checkout.
3. **Make the profile discoverable**:
   - Ensure the domain is crawlable and the well-known URL is linked or registered where Google expects (e.g. [Google Merchant Center / UCP](https://developers.google.com/merchant/ucp) if there is a directory or verification step).
   - So when Google’s AI Mode or Gemini needs products for a query, it can resolve our business and call our catalog API.

**What we need to build**

- **`/.well-known/ucp`** endpoint (or static file) returning our UCP profile (version, capabilities, REST/MCP schema URLs, endpoint base URL).
- **Catalog API** that UCP expects: e.g. search/list products and return items with `id`, `title`, `price` (integer cents), optional `image_url`. This can wrap our existing discovery service (`/api/v1/discover`) and map responses to UCP Item shape.
- **Checkout/order APIs** if we want full UCP checkout (create checkout, update, complete, order confirmation, webhooks). Optional for “discovery only.”
- **Public base URL** and, if required, registration/verification with Google’s UCP program.

Then **detection is ensured** by (1) our profile being discoverable and (2) our catalog API returning compliant data when the platform calls.

**Merchant attribution (UCP)**: In catalog and checkout responses, include the actual merchant (partner) per item where the schema allows (e.g. `seller_name` or custom fields). Our checkout API already operates on line items that may come from multiple partners; we keep resolving each item to its `partner_id` and handling splits and fulfillment per partner, same as today.

### 3.1 How to make Gemini look up products using UCP

Two ways Gemini can “look up” products with UCP:

| Path | What happens | What we need |
|------|----------------|---------------|
| **Native UCP (Google discovers us)** | User searches in Gemini / Google AI Mode → Google discovers our business via `/.well-known/ucp` → Google calls **our** catalog API → we return UCP Item–shaped products. | Implement `/.well-known/ucp` + UCP catalog API; make discoverable / register with Google. |
| **Our integration (Gemini calls orchestrator)** | User talks to a Gemini app that uses our tool → Gemini calls our `POST /api/v1/chat` → we return products. To be **UCP-compliant**, the response items should use UCP Item shape. | Ensure chat/orchestrator response (or discovery response) includes `id`, `title`, `price` (cents), optional `image_url` per product. |

**To enable native UCP (Gemini/Google calls our catalog):**

1. **Add `/.well-known/ucp`**  
   On the **public base URL** of the service that will serve UCP (e.g. discovery service or a dedicated gateway), expose `GET /.well-known/ucp` returning a UCP profile JSON:
   - `version`, `capabilities` (e.g. catalog search), REST/MCP schema URLs, base URL.  
   - Spec: [UCP Specification](https://ucp.dev/specification/overview/), [Schema Reference](https://ucp.dev/specification/reference/).

2. **Add a UCP catalog (search) API**  
   Implement an endpoint the platform can call to search/browse products (e.g. `GET /api/v1/ucp/catalog` or `GET /api/v1/ucp/items?q=...`). Response must return items in **UCP Item** shape:
   - **Required**: `id`, `title`, `price` (integer **cents**).
   - **Optional**: `image_url`.  
   This can **wrap** our existing discovery: call `/api/v1/discover` (or the orchestrator) and map each product to `{ "id": "...", "title": "...", "price": <cents>, "image_url": "..." }` (see `services/discovery-service/protocols/ucp_compliance.py` for validation and field mapping).

3. **Make the profile discoverable**  
   Ensure the domain is crawlable; link or register `/.well-known/ucp` where Google expects (e.g. [Google Merchant Center / UCP](https://developers.google.com/merchant/ucp)).

4. **(Optional)** Checkout/order APIs for full UCP checkout; not required for discovery-only.

**Current state:** We have UCP **compliance** (item validation, field mapping) in `services/discovery-service/protocols/ucp_compliance.py` and UCP **feed parsing** in `ucp_adapter.py` for manifest ingest. We do **not** yet expose a public `/.well-known/ucp` or a dedicated UCP catalog endpoint; those are the missing pieces for native Gemini/UCP discovery. For the **orchestrator + Gemini demo**, products are already returned when Gemini calls our tool; optionally ensure the API response shape matches UCP Item (id, title, price in cents, image_url) so any UCP consumer can use it.

---

## 4. Summary: ensuring detection

| Platform | Model | How we ensure products are detected |
|----------|--------|--------------------------------------|
| **ChatGPT (native search/shopping)** | Push feed (ACP) | Register with OpenAI, build ACP-compliant feed (jsonl.gz/csv.gz), deliver via hosted URL or their upload/SFTP, refresh regularly. Products then exist in ChatGPT’s index. |
| **Google AI Mode / Gemini (native)** | Expose API (UCP) | Publish `/.well-known/ucp`, implement catalog (and optionally checkout) APIs. Platform discovers us and calls our API; we don’t push into “their database.” |
| **ChatGPT / Gemini (our integration)** | Backend integration | Already ensured: they call our orchestrator → our discovery. Products live in our DB and are returned when the AI uses our endpoint. No ACP push or UCP endpoint required for this path. |

So: **ACP = we push into their system** (feed export + delivery + registration). **UCP = we expose our system** (well-known + catalog API + discoverability). Our current stack supports “AI calls us”; to support “native” discovery we add either (or both) the ACP feed pipeline or the UCP well-known + catalog layer.

---

## 5. Recommended next steps

1. **Decide which surface we care about first**: “Our” ChatGPT Actions / Gemini only → no extra work for detection. Native ChatGPT Search or Google AI Mode → need ACP feed and/or UCP API.
2. **For ACP**: Implement feed export (DB → ACP jsonl.gz), host it at a public URL or use OpenAI’s delivery, run ACP validation before export, then register and submit the feed.
3. **For UCP**: Add `/.well-known/ucp` and a catalog endpoint that returns UCP Item shape (id, title, price in cents, optional image_url) from our discovery; optionally add checkout/order flows and register with Google.

See [COMMERCE_FEED_SCHEMA_REQUIREMENTS.md](./COMMERCE_FEED_SCHEMA_REQUIREMENTS.md) for field requirements and [ACP_COMPLIANCE.md](./ACP_COMPLIANCE.md) for ACP validation.
