# Implementation Review: Distributed Business Agent (A2A) and Experience Tags

**Document version:** 1.0  
**Date:** 2025-01-28  
**Sources:** [implementation-status-distributed-business-agent-a2a.md](implementation-status-distributed-business-agent-a2a.md), [EXPERIENCE_TAGS.md](EXPERIENCE_TAGS.md)

This review details the implementation of the Distributed Business Agent (Merchant) A2A refactor and the experience-tag discovery and theme-bundles feature set, with explicit references to the status document and the Experience Tags design.

---

## 1. Overview

The implementation spans three main areas:

1. **Multi-Agent Discovery (design + encapsulation)** — Internal Business Agent uses experience_tags and product_capability_mappings internally; only UCP-shaped products and prices are exposed to the Planner.
2. **Exclusive Gateway (Seller of Record)** — Private registry, ID masking, single USO well-known on the Orchestrator, Scout refactor to query internal agents from the registry, and X-Gateway-Signature handshake.
3. **Experience-tag discovery and theme bundles** — End-to-end support for filtering/boosting by experience tag, GET experience-categories, discover_composite theme picking, and intent/tools schema for experience_tags and theme_experience_tag.

The **Experience Tags** design ([EXPERIENCE_TAGS.md](EXPERIENCE_TAGS.md)) defines the schema and usage of `experience_tags` on products and is implemented across discovery, ranking, and composite flows.

---

## 2. Experience Tags: Schema and Usage

### 2.1 Schema (from EXPERIENCE_TAGS.md)

| Aspect | Detail |
|--------|--------|
| **Table** | `products` |
| **Column** | `experience_tags` — JSONB, default `[]` |
| **Values** | Array of strings, lowercase (e.g. `["luxury", "night out", "travel", "celebration"]`) |
| **Index** | GIN on `experience_tags` for containment queries |
| **Migration** | `supabase/migrations/20250128000036_products_experience_tags.sql` |

### 2.2 Capability tags vs experience tags

| | capability_tags / capabilities | experience_tags |
|--|-------------------------------|------------------|
| **Purpose** | Category/capability (what the product is) | Thematic/experience (when/how it fits) |
| **Examples** | limo, flowers, dinner_reservation | luxury, night out, travel, celebration |
| **Storage** | `capability_tags` table + `products.capabilities` JSONB | `products.experience_tags` JSONB |
| **Use** | Intent/discovery category matching, filters | Search/recommendations by theme or occasion |

### 2.3 Partner portal

On the Products page, the **Experience tags** field accepts comma-separated tags; the API normalizes to lowercase and stores up to 20 tags.

### 2.4 Discovery usage (implemented)

- **Discovery service** selects and uses `experience_tags` for filtering (DB and semantic RPC), ranking boost, and internal theme matching; public responses strip `experience_tags` via `_product_for_public_response()` (Multi-Agent encapsulation).
- **Semantic search** includes `experience_tags` in the returned dict and supports optional `filter_experience_tag` in the `match_products` RPC.
- **Recommendations / discover_composite** filter or boost by experience_tags and pick best product per theme via `_pick_best_product_for_theme(products, experience_tags)`.

---

## 3. Multi-Agent Discovery (Design + Encapsulation)

**Status:** Implemented.  
**Reference:** [implementation-status-distributed-business-agent-a2a.md](implementation-status-distributed-business-agent-a2a.md) — “Multi-Agent Discovery (design + encapsulation)”.

### 3.1 Boundary

- **Internal (Discovery):** experience_tags, product_capability_mappings, and SQL/text search are used only inside the Internal Business Agent.
- **External (Planner / clients):** Only UCP-shaped data (products with id, name, description, price, currency, capabilities, etc.) is returned. No `experience_tags`, internal schema, or SQL is exposed.

### 3.2 Implementation

- **Response shape:** Discover and get_product use `_product_for_public_response(product)` in [services/discovery-service/api/products.py](services/discovery-service/api/products.py), which strips `experience_tags` (and optionally `partner_id` when ID masking is on).
- **Data flow:** Scout and DB/semantic layers use experience_tags for filter and boost; the API layer applies `_product_for_public_response()` before returning so Planner/UCP clients never see internal fields.

---

## 4. Exclusive Gateway (Seller of Record)

**Status:** Implemented (opt-in via env).  
**Reference:** [implementation-status-distributed-business-agent-a2a.md](implementation-status-distributed-business-agent-a2a.md) — “Exclusive Gateway (Seller of Record)”.

### 4.1 Private registry

| Item | Implementation |
|------|----------------|
| **Storage** | Table `internal_agent_registry` (capability, base_url, display_name, enabled). Migration: `supabase/migrations/20250128100000_internal_agent_registry.sql`. |
| **Access** | `get_internal_agent_urls(capability?: str)` in [services/discovery-service/db.py](services/discovery-service/db.py). Returns list of base URLs for aggregator; never exposed in APIs or manifests. |
| **Scout** | [services/discovery-service/scout_engine.py](services/discovery-service/scout_engine.py) `_fetch_via_aggregator` calls `get_internal_agent_urls()`; when non-empty, builds `UCPManifestDriver` so internal agents are queried in parallel with LocalDB. |

### 4.2 ID masking

| Item | Implementation |
|------|----------------|
| **Storage** | Table `id_masking_map` (masked_id, internal_product_id, partner_id, source). Migration: `supabase/migrations/20250128100001_id_masking_map.sql`. |
| **Functions** | `mask_product_id()`, `resolve_masked_id()`, `mask_products()` in [services/discovery-service/db.py](services/discovery-service/db.py). Masked id format: `uso_` + 24-char hex. |
| **Apply** | When `ID_MASKING_ENABLED=true` (Discovery config), discover and get_product return masked ids; `mask_products()` strips `partner_id` from response. |
| **Resolve** | add_product_to_bundle, add_products_to_bundle_bulk, and create_bundle_from_ucp_items resolve masked id to internal id before DB operations. |

### 4.3 Single USO well-known

| Item | Implementation |
|------|----------------|
| **Manifest** | Orchestrator exposes `GET /.well-known/ucp` in [services/orchestrator-service/api/gateway_ucp.py](services/orchestrator-service/api/gateway_ucp.py). Manifest points to Gateway base (`GATEWAY_PUBLIC_URL`) for REST endpoint and schema. |
| **Proxy routes** | `GET /api/v1/gateway/ucp/items`, `POST /api/v1/gateway/ucp/checkout`, `GET /api/v1/gateway/ucp/rest.openapi.json` proxy to Discovery service. |
| **Config** | `GATEWAY_PUBLIC_URL` (or `ORCHESTRATOR_PUBLIC_URL`) in Orchestrator config. |

### 4.4 X-Gateway-Signature

| Item | Implementation |
|------|----------------|
| **Signing / verification** | [packages/shared/gateway_signature.py](packages/shared/gateway_signature.py): `sign_request(method, path, body, secret)` and `verify_request(...)`; HMAC-SHA256 over method, path, body hash, timestamp; 5-minute replay window. |
| **Discovery** | Middleware in [services/discovery-service/middleware/gateway_signature.py](services/discovery-service/middleware/gateway_signature.py) requires `X-Gateway-Signature` and `X-Gateway-Timestamp` on `/api/*` when `GATEWAY_SIGNATURE_REQUIRED=true`. Public paths (e.g. `/health`, `/.well-known/`) are excluded. |
| **Orchestrator** | [services/orchestrator-service/clients.py](services/orchestrator-service/clients.py) `_gateway_headers_for_discovery(method, path, body)` adds headers to all Discovery requests when `GATEWAY_INTERNAL_SECRET` is set. |

---

## 5. Experience-Tag Discovery and Theme Bundles (Checklist)

**Status:** All 13 items implemented.  
**Reference:** [implementation-status-distributed-business-agent-a2a.md](implementation-status-distributed-business-agent-a2a.md) — “Experience-tag discovery and theme bundles (checklist)”.

| # | Area | Implementation |
|---|------|----------------|
| 1 | Semantic return | [services/discovery-service/semantic_search.py](services/discovery-service/semantic_search.py): `experience_tags` in `select_cols` and in returned dict. |
| 2 | DB filter | [services/discovery-service/db.py](services/discovery-service/db.py): `experience_tag` param; `.contains("experience_tags", [experience_tag.strip()])`. |
| 3 | Semantic RPC | Migration `20250128000037_match_products_experience_tag.sql`: `match_products` has `filter_experience_tag`; WHERE uses `experience_tags ? filter_experience_tag`. |
| 4 | Semantic call | [services/discovery-service/semantic_search.py](services/discovery-service/semantic_search.py): passes `filter_experience_tag` in RPC kwargs when `experience_tag` provided. |
| 5 | Aggregator | [packages/shared/discovery_aggregator.py](packages/shared/discovery_aggregator.py): `LocalDBDriver.search()` and `DiscoveryAggregator.search()` accept and pass `experience_tag`. |
| 6 | Scout | [services/discovery-service/scout_engine.py](services/discovery-service/scout_engine.py): `experience_tag` and `experience_tag_boost_amount` in `search()`, `_fetch_and_rank()`, `_fetch_via_aggregator()`; passed into `_apply_ranking`. |
| 7 | Ranking | [packages/shared/ranking.py](packages/shared/ranking.py): `sort_products_by_rank(..., experience_tag_boost=..., experience_tag_boost_amount=0.2)`; products whose `experience_tags` contain the tag get score boost. |
| 8 | Discover API | [services/discovery-service/api/products.py](services/discovery-service/api/products.py): GET `/api/v1/discover` has optional `experience_tag` query param; passed to scout `search()`. |
| 9 | Experience-categories API | GET `/api/v1/experience-categories` in products router; RPC `get_distinct_experience_tags()` (migration `20250128000038_get_distinct_experience_tags.sql`); [services/discovery-service/db.py](services/discovery-service/db.py) `get_distinct_experience_tags()`. Response: `{ "data": { "experience_categories": ["..."] } }`. |
| 10 | Orchestrator client | [services/orchestrator-service/clients.py](services/orchestrator-service/clients.py): `discover_products(..., experience_tag=...)`; `resolve_intent(..., experience_categories=...)`. |
| 11 | discover_composite | [services/orchestrator-service/agentic/loop.py](services/orchestrator-service/agentic/loop.py): `_pick_best_product_for_theme(products, experience_tags)`; suggested_bundle_options built by best match to option’s `experience_tags`; each option includes `experience_tags`; `theme_experience_tag` passed to `discover_products_fn`. |
| 12 | Intent prompt + API | [services/intent-service/api/resolve.py](services/intent-service/api/resolve.py): `ResolveRequest.experience_categories`; [services/intent-service/llm.py](services/intent-service/llm.py): `resolve_intent(..., experience_categories=...)`; user message injects available categories; response includes `bundle_options` (with `experience_tags`) and `theme_experience_tag`. |
| 13 | Tools | [services/orchestrator-service/agentic/tools.py](services/orchestrator-service/agentic/tools.py): discover_composite tool schema includes `experience_tags` per bundle option and optional `theme_experience_tag`; passed through in `execute_tool`. |

---

## 6. Not Implemented / Optional

**Reference:** [implementation-status-distributed-business-agent-a2a.md](implementation-status-distributed-business-agent-a2a.md) — “Not implemented / optional”.

- Multiple experience_tags filter (OR/AND) in a single request: **implemented** (AND semantics via `experience_tags` list; see status doc).
- **User input as theme to filter:** Implemented. Intent resolves natural language to `theme_experience_tag` or `theme_experience_tags`; discover/discover_composite receive these and Discovery filters (and boosts) by them. The user’s words are the theme input.
- Frontend “theme” badge or picker UI: **out of scope** for this repo (backend only). APIs support `experience_tag`/`experience_tags` so a client can implement a theme selector that calls discover with selected tag(s).
- Orchestrator pre-fetch of GET experience-categories and pass into resolve_intent on every resolve: **implemented** (resolve_intent_with_fallback calls get_experience_categories and passes to resolve_intent).

---

## 7. Configuration and Rollout

### 7.1 Experience tags

- No feature flag required; schema and discovery usage are always available.
- Partner portal: Experience tags field on product edit; stored in `products.experience_tags`.

### 7.2 Exclusive Gateway (opt-in)

| Variable | Service | Purpose |
|----------|---------|---------|
| `ID_MASKING_ENABLED` | Discovery | When `true`, discover/get_product return masked ids; add-to-bundle/checkout resolve masked id. |
| `GATEWAY_SIGNATURE_REQUIRED` | Discovery | When `true`, `/api/*` requires valid `X-Gateway-Signature` and `X-Gateway-Timestamp`. |
| `GATEWAY_INTERNAL_SECRET` | Discovery + Orchestrator | Shared secret for signing (Orchestrator) and verification (Discovery). |
| `GATEWAY_PUBLIC_URL` | Orchestrator | Public base URL for `/.well-known/ucp` manifest. |

---

## 8. Summary

- **Experience Tags** ([EXPERIENCE_TAGS.md](EXPERIENCE_TAGS.md)): Schema (JSONB, GIN index), partner portal, and distinction from capability tags are documented and implemented; discovery uses experience_tags for filter, boost, and theme-based product selection.
- **Multi-Agent Discovery:** Encapsulation is enforced; public discover and get_product responses strip `experience_tags` so the Planner sees only UCP-shaped products and prices.
- **Exclusive Gateway:** Private registry, ID masking, single USO well-known on Orchestrator with proxy routes, Scout integration with registry for UCP driver, and X-Gateway-Signature are implemented and can be enabled via the configuration above.
- **Experience-tag discovery and theme bundles:** All 13 checklist items are implemented end-to-end (semantic/DB filter and boost, discover API, experience-categories endpoint, discover_composite theme picking, intent and tools schema).

For the latest status and any follow-ups, see [implementation-status-distributed-business-agent-a2a.md](implementation-status-distributed-business-agent-a2a.md).
