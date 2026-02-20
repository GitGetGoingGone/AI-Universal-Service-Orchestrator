# Distributed Business Agent (Merchant) architecture – A2A refactor

## Multi-Agent Discovery (updated)

When the Planner broadcasts an intent (e.g. **"romantic date night"**), the **Internal Business Agent** (Merchant / Discovery) must:

1. **Internally** use:
   - **experience_tags** (e.g. map "romantic date night" → tags like `romantic`, `night out`, `celebration`)
   - **product_capability_mappings** (e.g. capabilities like `flowers`, `restaurant`, `movies` and their mapping to categories/slots)
   to resolve the intent to concrete products and bundles.

2. Return only a **standardized UCP response** (e.g. UCP Item list, prices, optional bundle structure). No internal identifiers, tags, or query details may be exposed in the response.

**Planner visibility:** The Planner (and Orchestrator) **only see the resulting Products and Prices**. They must **never** see:
- The underlying **experience_tags** used to match the intent
- The **product_capability_mappings** or category logic
- Any **SQL or database schema** used to find the products

So the boundary is strict: intent in (e.g. "romantic date night") → UCP products and prices out. All tag-based and SQL logic stays inside the Internal Business Agent.

---

## Implementation implications

- **Internal Business Agent (Discovery):** Implement intent → experience_tags and intent → product_capability_mappings (and any SQL/text search) entirely inside the Merchant. The JSON-RPC method (e.g. `search_catalog` or `discover_composite`) accepts only intent-style parameters (e.g. `intent`, `experience_name`, optional `budget_max`, `location`). Response is strictly UCP-shaped (items with id, title, price, optional image_url, etc.; no `experience_tags` or capability keys in the response unless they are part of the UCP spec).
- **Planner / Orchestrator:** Consume only the UCP response (products, prices, bundle_id if applicable). Do not pass or display experience_tags, capability mappings, or SQL to the Planner or to the user.
- **Aggregation:** When multiple Business Agents (e.g. Merchant + partners) are queried, each returns the same UCP shape; the Orchestrator aggregates only these UCP results into a unified bundle. No merging of internal tags or schema across agents.

This update refines **Phase 4 (Multi-Agent Discovery)** and **Phase 3 (Encapsulate Discovery as Merchant Agent)** so that experience_tags and product_capability_mappings are explicitly called out as internal implementation details of the Internal Business Agent, and the Planner only ever sees Products and Prices in UCP form.

---

## Exclusive Gateway (Seller of Record) architecture

Refactor the USO into an **Exclusive Gateway** so that the platform is the **Seller of Record** to the outside world. All public discovery, session, and checkout flows go through the USO; internal Business Agents and partner URLs stay private and are never exposed.

### 1. Private Registry and Masking

- **InternalRegistry:** Implement an internal registry that maps **generic capability names** (e.g. `flowers`, `restaurant`, `limo`) to **private partner / Business Agent URLs**. These URLs are used only by the Gateway for server-side calls and must **not** be exposed in any public-facing JSON, manifest, or API response.
- **ID masking:** All `product_id` and `service_id` values returned to the user (or to clients) must be **prefixed or mapped** to a USO-specific ID (e.g. `uso_` prefix or a stable opaque ID managed by the Gateway). This prevents direct discovery of the original merchant or partner; the user and external systems only ever see USO-owned identifiers. The Gateway maintains the mapping (USO id → internal agent + internal id) for checkout and fulfillment.

### 2. Unified UCP Manifest

- **Single well-known:** Generate **one** comprehensive `/.well-known/ucp` file for the **USO** (the Gateway). This manifest must claim **ownership** of all capabilities provided by the internal Business Agents (e.g. discovery, session, checkout). No internal agent URLs or partner URLs appear in this manifest.
- **All endpoints on the Gateway:** The UCP manifest’s endpoints for **discovery**, **session**, and **checkout** must all point to the **USO Gateway** (e.g. `https://uso-gateway.example.com/api/v1/...`), never to internal agents or partners. External clients (including AI platforms and frontends) discover and call only the Gateway.

### 3. Internal Orchestration Logic

- **ScoutEngine refactor:** Refactor the ScoutEngine (or equivalent discovery layer) so that it **queries the private internal agents in parallel** using the InternalRegistry. It uses only private URLs and does not expose them in responses.
- **Flatten to single UCP list:** The Orchestrator must **flatten** the responses from multiple internal agents into a **single UCP-compliant list** (e.g. one list of items, one basket/checkout view). All returned IDs are already masked to USO identifiers. To the outside world, the USO acts as the **Primary Merchant**; the fact that results are aggregated from multiple internal agents is an implementation detail.

### 4. Secure Internal Handshake

- **Middleware on Business Agents:** Implement middleware on each internal Business Agent that **rejects any direct traffic** (from the public internet or from clients that are not the Gateway) unless the request carries a **verified `X-Gateway-Signature`** (or equivalent header) from the USO.
- **Signing and verification:** The USO Gateway signs outbound requests to internal agents (e.g. HMAC or signed JWT over request details + secret). Each Business Agent verifies the signature using a shared secret or public key; requests without a valid signature are rejected (e.g. 401 or 403). This ensures that only the Gateway can call internal agents; direct access is blocked.

---

## Experience-tag discovery and theme bundles (incorporated plan)

*Source: experience-tag_discovery_and_theme_bundles_1cf22581.plan.md*

**Overview:** Add experience-tag-based discovery (return tags from semantic search, filter and rank/boost by tag), expose experience categories to the model, and extend the composite flow so the model suggests 3–4 theme bundles (with experience_tags); products are matched to each bundle by experience_tag and users pick a theme then choose products within it.

### Current state (reference)

- **Discovery:** Products have `experience_tags` (JSONB); DB search returns them; aggregator `UCPProduct` and `to_dict()` include them. Semantic search does **not** return `experience_tags`; there is no filter or boost by tag.
- **Composite flow:** Intent returns `search_queries` and `bundle_options`. `_discover_composite` calls `discover_products(query)` once per category, then builds 3–4 suggested bundles. No theme/experience_tag in the loop.
- **Intent:** Returns `intent_type`, `search_queries`, `bundle_options`; no experience categories or theme bundles today.

### 1. Return experience_tags from semantic search

- **File:** [services/discovery-service/semantic_search.py](services/discovery-service/semantic_search.py) — Add `"experience_tags"` to `select_cols` when building the returned list so the semantic path returns the same shape as DB search and includes `experience_tags`.
- RPC `match_products` already returns full row; only Python normalization is updated.

### 2. Filter products by experience tag

- **Discovery API:** [services/discovery-service/api/products.py](services/discovery-service/api/products.py) — Add optional `experience_tag: Optional[str] = Query(None)`; pass to `search()`.
- **Scout engine:** [services/discovery-service/scout_engine.py](services/discovery-service/scout_engine.py) — Add `experience_tag` to `search()`, `_fetch_and_rank()`, `_fetch_via_aggregator()`; pass to `search_products()` / `semantic_search()`.
- **DB:** [services/discovery-service/db.py](services/discovery-service/db.py) — Add `experience_tag` to `search_products()`; when set, filter with `.contains("experience_tags", [experience_tag])`.
- **Semantic path:** New migration — alter `match_products` to add optional `filter_experience_tag text`; WHERE with `experience_tags ? filter_experience_tag`. [semantic_search.py](services/discovery-service/semantic_search.py) — pass `filter_experience_tag` to RPC when `experience_tag` provided.
- **Aggregator:** [packages/shared/discovery_aggregator.py](packages/shared/discovery_aggregator.py) — Add `experience_tag` to `LocalDBDriver.search()` and `DiscoveryAggregator.search()`.
- **Orchestrator client:** [services/orchestrator-service/clients.py](services/orchestrator-service/clients.py) — Add `experience_tag` to `discover_products()`; pass to discovery service.

### 3. Rank/boost by experience tag

- **File:** [packages/shared/ranking.py](packages/shared/ranking.py) — Add `experience_tag_boost: Optional[str] = None` (and optionally `experience_tag_boost_amount: float = 0.2`) to `sort_products_by_rank()`. When set, add boost to score for products whose `experience_tags` contains that tag.
- **Scout:** [services/discovery-service/scout_engine.py](services/discovery-service/scout_engine.py) — When `experience_tag` provided, pass into `_apply_ranking`; call `sort_products_by_rank(..., experience_tag_boost=experience_tag)`.

### 4. Experience-tag-based categories (list for the model)

- **New endpoint:** GET `/api/v1/experience-categories` in discovery service. Returns distinct experience tag values (e.g. Supabase RPC `get_distinct_experience_tags()`). Response: `{ "data": { "experience_categories": ["baby", "celebration", "gift", "luxury", "night out", "romantic", "travel"] } }`.
- **Orchestrator/Intent:** Orchestrator can call GET experience-categories and pass list into resolve_intent so the model knows available experience categories.

### 5. Theme bundles: model suggests 3–4 bundles; match products by theme

- **Intent:** Extend system/DB prompt so model returns 3–4 theme bundle options with `label`, `description`, `categories`, and **`experience_tags`** (e.g. `["romantic"]`). Extend API contract: `bundle_options: [{ label, description, categories, experience_tags }]`. Intent API and [llm.py](services/intent-service/llm.py) accept optional `experience_categories: List[str]` and inject into message.
- **discover_composite:** [services/orchestrator-service/agentic/loop.py](services/orchestrator-service/agentic/loop.py) — After building `category_products`, for each of 3–4 `suggested_bundle_options` use option’s `experience_tags`: for each category, sort `_get_products_for_category(cat)` by best match to option’s experience_tags; pick first. Helper e.g. `_pick_best_product_for_theme(products, experience_tags)`. Add optional `experience_tags` to each suggested option. Optionally pass `theme_experience_tag` to `discover_products_fn` when intent sets it.
- **Tools:** [services/orchestrator-service/agentic/tools.py](services/orchestrator-service/agentic/tools.py) — discover_composite: allow `experience_tags` in bundle_options; optional `theme_experience_tag`.

### 6. End-to-end wiring

- Orchestrator: fetch experience categories (GET discovery experience-categories); pass into resolve_intent. Intent returns `bundle_options` with `experience_tags` per option. discover_composite: for each category call discover_products(…, experience_tag=theme_experience_tag if desired); build suggested_bundle_options by picking best product per category per option by experience_tags; attach option’s experience_tags to suggested_bundle_options.

### File checklist (experience-tag plan)

| # | Area | File(s) | Change |
|---|------|--------|--------|
| 1 | Semantic return | semantic_search.py | Add `experience_tags` to returned dict |
| 2 | DB filter | db.py | Add `experience_tag` param; filter with `.contains("experience_tags", [tag])` |
| 3 | Semantic RPC | New migration | `match_products` add `filter_experience_tag`; WHERE with `experience_tags ? filter_experience_tag` |
| 4 | Semantic call | semantic_search.py | Pass `filter_experience_tag` to RPC |
| 5 | Aggregator | discovery_aggregator.py | Add `experience_tag` to LocalDBDriver and DiscoveryAggregator.search |
| 6 | Scout | scout_engine.py | Add `experience_tag` to search, _fetch_and_rank, _fetch_via_aggregator; pass to ranking |
| 7 | Ranking | ranking.py | Add experience_tag_boost to sort_products_by_rank |
| 8 | Discover API | api/products.py | Add `experience_tag` query param; pass to search() |
| 9 | Experience-categories API | New RPC + api/products.py or router | GET /experience-categories using RPC get_distinct_experience_tags |
| 10 | Orchestrator client | clients.py | Add `experience_tag` to discover_products |
| 11 | discover_composite | loop.py | Build suggested_bundle_options by picking best product per category per option by experience_tags; optional theme_experience_tag |
| 12 | Intent prompt + API | Intent system prompt; llm.py; intent API | experience_categories; return bundle_options with experience_tags; accept experience_categories in resolve_intent |
| 13 | Tools | tools.py | discover_composite: allow experience_tags in bundle_options; optional theme_experience_tag |

### Out of scope / follow-ups (experience-tag)

- Multiple experience_tags filter (OR/AND) in one request.
- Frontend UI for “theme” badge or filtering by selected theme in refine flow.
- Persisting “selected theme bundle” in state (current state already keeps suggested_bundle_options).
