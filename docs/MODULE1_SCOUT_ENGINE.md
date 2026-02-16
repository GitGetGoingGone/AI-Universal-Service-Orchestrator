# Module 1: Scout Engine – How It Works & How to Test

This document explains how **semantic search**, the **scout engine**, and **protocol adapters** (UCP/ACP) work, and gives concrete options to test them.

**ACP (OpenAI Product Feed) compliance**: To ensure products align with the [OpenAI Product Feed Spec](https://developers.openai.com/commerce/specs/feed), see [ACP_COMPLIANCE.md](./ACP_COMPLIANCE.md) for validation, required fields, prohibited content, and how to use `validate_acp` on manifest ingest.

---

## 1. High-Level Flow

```
User / AI Agent
       │
       ▼
GET /api/v1/discover?intent=flowers
       │
       ▼
┌──────────────────┐
│   Scout Engine   │  ← Single entry point
│   (search())     │
└────────┬─────────┘
         │
         ├── Is it a "browse" query? (sample, demo, hi) ──► Text search, no filter
         │
         ├── use_semantic=True
         │        │
         │        ▼
         │   ┌─────────────────┐
         │   │ Semantic Search │  ← Azure OpenAI embed query → pgvector
         │   │ (match_products)│
         │   └────────┬────────┘
         │            │
         │            ├── Embeddings configured + products have embeddings?
         │            │   → Return similar products (cosine similarity)
         │            │
         │            └── No results or no embeddings? → fall through
         │
         └── Fallback: Text search (name/description ILIKE)
```

- **Scout engine** always decides: browse → text only; otherwise try semantic, then fallback to text.
- **Semantic search** only runs when embeddings are configured and products have embeddings.
- **Protocol adapters** are used when you **ingest** external feeds (UCP/ACP) via manifest URL; they do not run on every discover request.

---

## 2. Semantic Search in Detail

### What it is

- **Vector search**: user query and each product are turned into **embeddings** (1536‑dim vectors).
- **Similarity**: products whose embedding is “close” to the query embedding are returned (meaning similar in meaning, not just keyword match).

### Step-by-step

1. **Query embedding**
   - User query (e.g. `"birthday flowers for mom"`) is sent to **Azure OpenAI Embeddings** (`text-embedding-ada-002` or `text-embedding-3-small`, 1536 dimensions).
   - You get a vector `[0.012, -0.034, ...]`.

2. **Database search (pgvector)**
   - That vector is passed to the Supabase RPC **`match_products`**.
   - In Postgres, the function:
     - Filters: `deleted_at IS NULL`, `embedding IS NOT NULL`, optional `partner_id` / `exclude_partner_id`.
     - Keeps rows with similarity above `match_threshold`: `(1 - (embedding <=> query_embedding)) > match_threshold` (cosine: `<=>` is distance, so `1 - distance` = similarity).
     - Orders by **cosine distance** (`embedding <=> query_embedding`) ascending.
     - Returns up to `match_count` products.

3. **Product embeddings**
   - Each product’s embedding is built from: **name + description + capabilities** (see `_get_product_embedding_input` in `semantic_search.py`).
   - Embeddings are stored in `products.embedding` (column type `vector(1536)`).
   - They are **not** computed on every search; they are **precomputed** (e.g. when a product is created/updated or via **backfill**).

### When semantic search is used

- **Used**: Embedding config is in Platform Config. At least some products need non-null `embedding` for semantic search.
- **Not used** (fallback to text): embeddings not configured, or query embedding fails, or **no products have embeddings** (RPC returns nothing), or you explicitly call with `use_semantic=False` at the scout layer.

### Configuration

- **Discovery service** embedding config is in Platform Config (llm_providers).
- Migration **`20240128000011_scout_semantic_search.sql`** must be applied so the `match_products` RPC exists.

---

## 3. Scout Engine in Detail

**File**: `services/discovery-service/scout_engine.py`

**Role**: Single function `search(...)` that:

1. **Empty or browse query**
   - If query is empty or is a “browse” term (e.g. `sample`, `demo`, `hi`, `please`), it calls **text search only** with no text filter (returns recent products, optionally by partner).

2. **Normal query**
   - If `use_semantic=True` (default):
     - Calls **semantic_search(...)**.
     - If that returns at least one product, returns that list.
   - If semantic is off or returns nothing:
     - Calls **search_products(...)** (text search on `name` / `description` ILIKE).

3. **Parameters**
   - `query`, `limit`, `location` (reserved), `partner_id`, `exclude_partner_id`, `use_semantic`.

So: **scout engine = “try semantic first, else text,” plus special handling for browse.**

---

## 4. Protocol Adapters (UCP / ACP)

Adapters **parse external product feeds** into a **unified shape** (id, name, description, price, currency, url, image_url, etc.). They are used when **ingesting** a manifest from a URL, not when serving `/discover`.

### ACP (OpenAI Agentic Commerce Protocol)

- **Use case**: Feeds for ChatGPT / OpenAI commerce (e.g. JSONL/JSON product feed).
- **File**: `protocols/acp_adapter.py` → **`parse_acp_feed(data)`**.
- **Expects** (per item): `item_id` or `id`, `title` or `name`, `description`, `price` (e.g. `"79.99 USD"`), `url`, `image_url`, `availability`, `brand`, `is_eligible_search` (optional; if false, item is skipped).
- **Accepts**: A **list** of items, or a **dict** with key `"products"` or `"items"`.
- **Output**: List of normalized product dicts (e.g. `id`, `name`, `description`, `price`, `currency`, `url`, `image_url`, `availability`, `brand`, `capabilities`, `metadata.source = "acp"`).

### UCP (Google Universal Commerce Protocol)

- **Use case**: Feeds for Google (Search AI Mode, Gemini).
- **File**: `protocols/ucp_adapter.py` → **`parse_ucp_feed(data)`**.
- **Expects** (per item): `itemId` / `id` / `identifier` / `sku`, `name` / `title`, `description`, `offers` (with `price`, `priceCurrency`) or `offer`, `url` / `productUrl`, `image` / `image_url`, `availability`, `brand` (string or `{ "name": "..." }`).
- **Accepts**: A **list** of items, or a **dict** with key `"products"`, `"items"`, `"itemListElement"`, or `"offers"`.
- **Output**: Same unified shape, with `metadata.source = "ucp"`.

### Where they are used

- **Manifest ingest**: `POST /api/v1/admin/manifest/ingest` with body `{ "partner_id", "manifest_url", "manifest_type": "acp" | "ucp" }`.
- **Flow**:
  1. Service fetches the URL (with HTTP cache: etag / last-modified).
  2. Parses JSON (or JSONL) from the response.
  3. Calls **`parse_acp_feed`** or **`parse_ucp_feed`** depending on `manifest_type`.
  4. Stores the **parsed product list** in **`partner_manifests`** (and cache metadata in **`manifest_cache`**).
- **Note**: Ingest currently **caches** the parsed list; it does **not** automatically insert those products into the **`products`** table or backfill embeddings. So discovery (semantic or text) still runs against **`products`** in Supabase. To use manifest data in discovery, you’d add a separate step (e.g. “sync manifest products into `products`” and then backfill embeddings).

---

## 5. Connecting to external feeds (no hosting)

There are **no official public “ACP servers” or “UCP servers”** you can point at like a single API. Both protocols assume **you or the merchant** host the feed:

- **ACP (OpenAI)**: Merchants register at [chatgpt.com/merchants](https://chatgpt.com/merchants) and provide their **own** product feed URL (or upload). OpenAI ingests that URL. There is no public OpenAI-run ACP catalog to connect to.
- **UCP (Google)**: Stores publish a `/.well-known/ucp` and catalog endpoints on **their own** domain. The [UCP Playground](https://ucp.dev/playground/) is a **browser-only simulation** with mocked data, not a live server you can call.

So for testing **without hosting your own file**, you can use the following.

### Public / third-party feeds that work with our adapters

| Source | URL | Use as | Notes |
|--------|-----|--------|--------|
| **FakeStoreAPI** | `https://fakestoreapi.com/products` | ACP-style | Returns a JSON **array** of products. Our ACP adapter accepts arrays and maps `id`, `title`, `description`, `price`, `image` → `image_url`. No auth. Use with `manifest_type=acp`. |
| **FakeStoreAPI (by category)** | `https://fakestoreapi.com/products/category/electronics` etc. | ACP-style | Same shape, smaller set. |
| **Your own static JSON** | Any public URL (e.g. GitHub raw, S3, pastebin) | ACP or UCP | Host a single JSON file with `{"products": [...]}` (ACP) or `{"items": [...]}` (UCP) and use that URL as `manifest_url`. |

### Example: use FakeStoreAPI as your “ACP” feed (no hosting)

1. Pick a valid **partner_id** (UUID of a partner in your `partners` table).
2. Call manifest ingest with FakeStoreAPI as the URL:

   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/manifest/ingest" \
     -H "Content-Type: application/json" \
     -d '{
       "partner_id": "YOUR_PARTNER_UUID",
       "manifest_url": "https://fakestoreapi.com/products",
       "manifest_type": "acp"
     }'
   ```

3. Response: `{"products_count": 20, "manifest_type": "acp"}` (or similar). Parsed products are stored in **`partner_manifests.manifest_data`**.

**CORS:** The discovery service runs server-side and fetches the URL from your backend, so browser CORS does not apply. FakeStoreAPI allows server requests.

### UCP: no public catalog server

For **UCP**, there is no public URL that serves a live product catalog you can plug in. Options:

- Use **UCP Playground** ([ucp.dev/playground](https://ucp.dev/playground/)) to understand the protocol (discovery → capability negotiation → checkout). It does not expose a feed URL.
- Use **sample code** from [Universal-Commerce-Protocol/samples](https://github.com/Universal-Commerce-Protocol/samples) to run a minimal UCP “store” locally and point `manifest_url` at your local catalog endpoint (then you are effectively hosting it).
- Host a **static JSON** file (e.g. UCP-style `{"items": [...]}`) on any public URL and use it with `manifest_type=ucp`.

### Summary

- **No hosted ACP/UCP “servers”** from OpenAI or Google to connect to; feeds are merchant- or self-hosted.
- **Without hosting:** Use **FakeStoreAPI** as `manifest_url` with `manifest_type=acp`, or any public URL that serves ACP- or UCP-shaped JSON.
- **With minimal hosting:** Put a static JSON file on GitHub raw, S3, or your own server and use that URL for ingest.

---

## 6. How to Test

### A. Test discovery (scout + text/semantic) without protocol adapters

**1. Text search only (no embeddings)**

- Don’t set embedding env vars, or ensure no product has `embedding` set.
- Call:
  ```bash
  curl "http://localhost:8000/api/v1/discover?intent=flowers&limit=5"
  ```
- You should get products whose **name or description** contains “flowers” (or recent products for browse terms like `intent=sample`).

**2. Semantic search (with embeddings)**

- Configure LLM/embedding via Platform Config UI at `/platform/config`.
- Apply migration: `supabase db push` (or equivalent) so **`match_products`** exists.
- Backfill at least one product:
  ```bash
  curl -X POST "http://localhost:8000/api/v1/admin/embeddings/backfill?product_id=<UUID_OF_PRODUCT>"
  ```
- Call discover again with a query that **matches that product by meaning** (e.g. “gifts for her” for a flowers product):
  ```bash
  curl "http://localhost:8000/api/v1/discover?intent=gifts%20for%20her&limit=5"
  ```
- You should see that product in the list when semantic search returns results.

**3. Browse vs search**

- Browse (no filter): `intent=sample` or `intent=demo` → recent products.
- Search: `intent=chocolates` → text or semantic results for “chocolates”.

---

### B. Test protocol adapters with manifest ingest

**1. ACP-style feed (JSON)**

- Host a JSON file (or use a public URL) that looks like this:
  ```json
  {
    "products": [
      {
        "item_id": "SKU-001",
        "title": "Red Roses Bouquet",
        "description": "Fresh red roses, 12 stems",
        "price": "29.99 USD",
        "url": "https://example.com/roses",
        "image_url": "https://example.com/roses.jpg",
        "availability": "in_stock",
        "brand": "FlowerCo",
        "is_eligible_search": true
      }
    ]
  }
  ```
- Ingest it (replace `PARTNER_UUID` and `https://your-server.com/feed.json`):
  ```bash
  curl -X POST "http://localhost:8000/api/v1/admin/manifest/ingest" \
    -H "Content-Type: application/json" \
    -d '{
      "partner_id": "PARTNER_UUID",
      "manifest_url": "https://your-server.com/feed.json",
      "manifest_type": "acp"
    }'
  ```
- Expected: `{"products_count": 1, "manifest_type": "acp"}`. The parsed products are stored in **`partner_manifests.manifest_data`** (not in `products` table yet).

**2. UCP-style feed (schema.org-like)**

- Example feed:
  ```json
  {
    "items": [
      {
        "id": "ucp-001",
        "name": "Dark Chocolate Box",
        "description": "Assorted dark chocolates",
        "offers": { "price": 24.99, "priceCurrency": "USD" },
        "url": "https://example.com/choc",
        "image": "https://example.com/choc.jpg",
        "availability": "in_stock",
        "brand": "ChocoBrand"
      }
    ]
  }
  ```
- Ingest:
  ```bash
  curl -X POST "http://localhost:8000/api/v1/admin/manifest/ingest" \
    -H "Content-Type: application/json" \
    -d '{
      "partner_id": "PARTNER_UUID",
      "manifest_url": "https://your-server.com/ucp-feed.json",
      "manifest_type": "ucp"
    }'
  ```
- Expected: `{"products_count": 1, "manifest_type": "ucp"}`. Again, data is in **`partner_manifests`**.

**3. Test adapters in isolation (optional)**

- In a Python shell from `services/discovery-service`:
  ```python
  from protocols.acp_adapter import parse_acp_feed
  from protocols.ucp_adapter import parse_ucp_feed

  acp = parse_acp_feed({"products": [{"item_id": "1", "title": "Test", "description": "D", "price": "10 USD"}]})
  ucp = parse_ucp_feed({"items": [{"id": "2", "name": "Test", "offers": {"price": 10, "priceCurrency": "USD"}}]})
  print(acp, ucp)
  ```

---

### C. End-to-end with semantic + adapters (future)

Today:

- **Manifest ingest** only fills **`partner_manifests`**; it does **not** insert into **`products`** or run backfill.
- **Discovery** only reads from **`products`** (and uses **`products.embedding`** for semantic).

So to “test protocol adapters with semantic search” end-to-end you would:

1. Ingest a UCP/ACP manifest (as above).
2. Add a separate job or endpoint that:
   - Reads from **`partner_manifests.manifest_data`**,
   - Upserts into **`products`** (with a `partner_id`),
   - Calls embedding backfill for those product IDs.
3. Then call **`/api/v1/discover?intent=...`** and confirm semantic results.

---

## 7. Quick reference

| What you want to test      | What to use                                                                 |
|----------------------------|-----------------------------------------------------------------------------|
| Text-only discovery        | `/discover?intent=...` with no embeddings configured                       |
| Semantic discovery         | Configure embedding via Platform Config, backfill products, then `/discover` |
| Scout browse behavior      | `/discover?intent=sample` or `intent=demo`                                 |
| ACP feed parsing           | Host ACP-style JSON, then `POST /api/v1/admin/manifest/ingest` with `manifest_type=acp` |
| UCP feed parsing           | Host UCP-style JSON, then `POST /api/v1/admin/manifest/ingest` with `manifest_type=ucp` |
| Embedding backfill         | `POST /api/v1/admin/embeddings/backfill?product_id=<uuid>`                  |

---

## 8. Summary

- **Semantic search**: Query and products are embedded with Azure OpenAI; Postgres **pgvector** (RPC **`match_products`**) returns products by cosine similarity; products need precomputed embeddings (e.g. via backfill).
- **Scout engine**: One `search()`: browse → text only; else try semantic, then fallback to text search.
- **Protocol adapters**: **UCP** and **ACP** parsers normalize external feeds; they are used by **manifest ingest** and write to **`partner_manifests`**; they do not drive `/discover` until you sync manifest data into **`products`** and backfill embeddings.
