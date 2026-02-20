# Implementation status: Distributed Business Agent (A2A refactor)

Status relative to [.cursor/plans/distributed-business-agent-a2a-refactor.md](.cursor/plans/distributed-business-agent-a2a-refactor.md).  
Last updated: 2025-01-28.

---

## Implemented

### Multi-Agent Discovery (design + encapsulation)

- Internal Business Agent uses experience_tags and product_capability_mappings internally and returns a standardized UCP response. Planner visibility boundary is enforced: discover and get_product responses use `_product_for_public_response()` to strip `experience_tags` (and optionally `partner_id` when ID masking is on) so Planner/UCP clients never see internal fields.

### Exclusive Gateway (Seller of Record)

- **Private Registry:** Table `internal_agent_registry` (capability, base_url, display_name, enabled); `get_internal_agent_urls(capability?)` in discovery `db.py`. Scout uses registry to build UCPManifestDriver when URLs are present.
- **ID masking:** Table `id_masking_map`; `mask_product_id` / `resolve_masked_id` / `mask_products()` in discovery `db.py`. Discover and get_product return masked ids when `ID_MASKING_ENABLED=true`; add-to-bundle, add-bulk, and UCP checkout resolve masked ids before DB.
- **Single USO well-known:** Orchestrator exposes `GET /.well-known/ucp` and proxy routes `GET /api/v1/gateway/ucp/items`, `POST /api/v1/gateway/ucp/checkout`, `GET /api/v1/gateway/ucp/rest.openapi.json` that forward to Discovery. Config: `GATEWAY_PUBLIC_URL`.
- **ScoutEngine + registry:** `_fetch_via_aggregator` calls `get_internal_agent_urls()` and, when non-empty, builds `UCPManifestDriver` so internal agents are queried in parallel with LocalDB; results merged and returned (masking applied at API layer when enabled).
- **X-Gateway-Signature:** Shared `packages/shared/gateway_signature.py` (sign_request, verify_request). Discovery middleware `gateway_signature_middleware` requires `X-Gateway-Signature` and `X-Gateway-Timestamp` on `/api/*` when `GATEWAY_SIGNATURE_REQUIRED=true`. Orchestrator clients add these headers to all Discovery requests when `GATEWAY_INTERNAL_SECRET` is set.

### Experience-tag discovery and theme bundles (checklist)

| # | Area | Status |
|---|------|--------|
| 1 | Semantic search return `experience_tags` | Done – `semantic_search.py` includes `experience_tags` in returned dict |
| 2 | DB filter by experience_tag | Done – `db.py` has `experience_tag` param; filter via `.contains("experience_tags", [tag])`; migration `20250128000037_match_products_experience_tag.sql` adds `filter_experience_tag` to RPC |
| 3 | Semantic RPC | Done – migration adds `filter_experience_tag` to `match_products` |
| 4 | Semantic call | Done – `semantic_search.py` passes `filter_experience_tag` when `experience_tag` provided |
| 5 | Aggregator | Done – `LocalDBDriver.search()` and `DiscoveryAggregator.search()` accept `experience_tag` |
| 6 | Scout | Done – `experience_tag` and `experience_tag_boost_amount` in `search()`, `_fetch_and_rank()`, `_fetch_via_aggregator()`; passed to ranking |
| 7 | Ranking | Done – `sort_products_by_rank()` has `experience_tag_boost` and `experience_tag_boost_amount` |
| 8 | Discover API | Done – GET `/api/v1/discover` has optional `experience_tag` and `experience_tags` (list, AND) query params; passed to scout `search()` |
| 9 | Experience-categories API | Done – GET `/api/v1/experience-categories`; RPC `get_distinct_experience_tags` (migration `20250128000038_get_distinct_experience_tags.sql`); `db.get_distinct_experience_tags()` |
| 10 | Orchestrator client | Done – `discover_products()` accepts `experience_tag` and `experience_tags`; `resolve_intent()` accepts `experience_categories`; `get_experience_categories()` for pre-fetch |
| 11 | discover_composite | Done – `_pick_best_product_for_theme(products, experience_tags)`; suggested_bundle_options built by best match to option’s `experience_tags`; `experience_tags` on each option; `theme_experience_tag` param passed to `discover_products_fn` |
| 12 | Intent prompt + API | Done – `ResolveRequest.experience_categories`; `resolve_intent(..., experience_categories=...)`; user message injects available categories; response includes `bundle_options` (with `experience_tags`) and `theme_experience_tag` for discover_composite/refine_composite |
| 13 | Tools | Done – discover_composite: `experience_tags` in bundle_options; optional `theme_experience_tag` and `theme_experience_tags`; passed through to `discover_composite_fn` |

### Exclusive Gateway (Seller of Record)

| Area | Status |
|------|--------|
| Private Registry | Done – table `internal_agent_registry` (migration `20250128100000_internal_agent_registry.sql`); `db.get_internal_agent_urls(capability?)` |
| ID masking | Done – table `id_masking_map`; `mask_product_id` / `resolve_masked_id` / `mask_products`; discover and get_product return masked ids when `ID_MASKING_ENABLED=true`; add-to-bundle and UCP checkout resolve masked id |
| Single USO well-known | Done – Orchestrator exposes `GET /.well-known/ucp` and proxy routes `GET/POST /api/v1/gateway/ucp/*` to Discovery; `GATEWAY_PUBLIC_URL` for manifest base |
| Scout + registry | Done – `_fetch_via_aggregator` builds `UCPManifestDriver` from `get_internal_agent_urls()` when registry has URLs; parallel query and flatten unchanged |
| X-Gateway-Signature | Done – `packages/shared/gateway_signature.py` (sign/verify); Discovery middleware requires header when `GATEWAY_SIGNATURE_REQUIRED=true`; Orchestrator clients add `X-Gateway-Signature` and `X-Gateway-Timestamp` to all Discovery calls when `GATEWAY_INTERNAL_SECRET` set |

### Multi-Agent Discovery (encapsulation)

- **Response shape:** Discover and get_product return only UCP-style fields; `_product_for_public_response` strips `experience_tags` from all public API responses. Planner/UCP clients do not see internal tags or schema.

---

## Not implemented / optional

### Optional / follow-ups (experience-tag plan)

- **Multi-tag filter (AND semantics):** **Implemented.** Discovery accepts `experience_tags` (list) in DB, semantic search (post-filter), scout, aggregator, and GET `/api/v1/discover`; orchestrator `discover_products(experience_tags=...)` and discover_composite `theme_experience_tags`; intent may return `theme_experience_tags` for e.g. "luxury travel-friendly night out."
- **User input as theme to filter:** **Implemented.** User natural language (e.g. "romantic dinner", "luxury travel-friendly night out") is resolved by intent to `theme_experience_tag` or `theme_experience_tags`, which are passed to discover/discover_composite; Discovery filters and boosts by those tags. No separate "theme" field is required—the user’s words drive the theme filter.
- **Frontend theme badge/picker UI:** **Out of scope** for this repo (backend/orchestrator only). The API supports `experience_tag` and `experience_tags` on discover, so a frontend can implement a theme selector (badge, dropdown, chips) that calls discover with the selected tag(s) if desired.
- **Automatic category pre-fetch:** **Implemented.** Orchestrator `resolve_intent_with_fallback()` calls `get_experience_categories()` (GET Discovery `/api/v1/experience-categories`) and passes the list to `resolve_intent(..., experience_categories=...)` so the intent LLM always has available tags for theme bundles without caller wiring.

---

## Deployment impact (rebuild / restart)

For the experience-tag, multi-tag filter, and automatic category pre-fetch changes:

| Service | Affected? | Action |
|--------|-----------|--------|
| **Discovery** | Yes | Restart required. Code: `db.py`, `semantic_search.py`, `api/products.py`, `scout_engine.py`; uses `packages/shared` (discovery_aggregator, ranking). |
| **Orchestrator** | Yes | Restart required. Code: `clients.py`, `api/chat.py`, `agentic/loop.py`, `agentic/tools.py`; uses `packages/shared` (e.g. gateway_signature). |
| **Intent** | Yes | Restart required. Code: `api/resolve.py`, `llm.py`. |
| **Shared package** (`packages/shared`) | Yes (library) | No standalone process. Picked up when Discovery or Orchestrator is restarted (they import from it). If you build Docker images per service, rebuild images that include `packages/shared` (typically Discovery and Orchestrator). |
| **Database** | No | No new migrations for multi-tag or pre-fetch. Existing schema (`experience_tags` on products, `get_distinct_experience_tags`, `match_products` with `filter_experience_tag`) is unchanged. |
| Other services (payment, proofing, webhook, etc.) | No | Not changed by this work. |

**Summary:** Restart **Discovery**, **Orchestrator**, and **Intent** so they load the new code. Rebuild images only if your deploy builds service-specific images (e.g. Docker); then rebuild and redeploy those three services.

---

## Summary

- **Experience-tag discovery and theme bundles:** Implemented end-to-end (semantic/DB filter and boost, discover API, experience-categories endpoint, discover_composite theme picking, intent and tools schema).
- **Exclusive Gateway:** Implemented (private registry, ID masking, single well-known on Orchestrator with proxy routes, Scout uses registry for UCP driver, X-Gateway-Signature middleware and client signing). Enable via `ID_MASKING_ENABLED`, `GATEWAY_SIGNATURE_REQUIRED`, and `GATEWAY_INTERNAL_SECRET` as needed.
- **Multi-Agent Discovery:** Public discovery responses strip `experience_tags`; Planner sees only products and prices (UCP shape).
