# Implementation status: Distributed Business Agent (A2A refactor)

**Plan:** [.cursor/plans/distributed-business-agent-a2a-refactor.md](../.cursor/plans/distributed-business-agent-a2a-refactor.md).  
**Status:** All planned A2A features below are implemented. Build and deploy: [HOW_TO_BUILD_AND_DEPLOY.md](HOW_TO_BUILD_AND_DEPLOY.md).  
Last updated: 2025-01-28.

---

## Implemented

### 1. LLM abstraction (Orchestrator)

- **Location:** `packages/shared/llm_provider/` (config, provider protocol, OSS provider, OpenAI fallback, facade).
- **Behavior:** Primary OSS endpoint + optional OpenAI fallback; `LLMProviderFacade.get_client()` for planner tool calls. Env: `LLM_PRIMARY`, `LLM_FALLBACK`, `OSS_ENDPOINT`, `OSS_API_KEY`, `OPENAI_API_KEY`, `LLM_TIMEOUT_SEC`, `LLM_MAX_RETRIES`.
- **Orchestrator:** `planner.py` uses facade when OSS or OpenAI env is set.

### 2. UCP-only signature middleware (Discovery)

- **Location:** `services/discovery-service/middleware/gateway_signature.py`.
- **Behavior:** Requests to `/api/v1/ucp/*` require `X-Gateway-Signature` when `GATEWAY_INTERNAL_SECRET` is set; POST/PUT/PATCH body verified and re-set for downstream; GET uses `verify_request_no_body`. Other `/api/*` unchanged (still behind optional `gateway_signature_required`).

### 3. match_products_v2 + semantic search

- **Migration:** `supabase/migrations/20250128120000_match_products_v2.sql` defines `match_products_v2` (same signature as `match_products`).
- **Discovery:** `semantic_search.py` calls `client.rpc("match_products_v2", kwargs)`.

### 4. Data hygiene (public product shape)

- **Location:** `packages/shared/ucp_public_product.py` — allow-list `PUBLIC_PRODUCT_ALLOWED_KEYS`, `STRIP_KEYS` (experience_tags, partner_id, internal_notes), `filter_product_for_public()`, `filter_products_for_public()`.
- **Discovery:** `api/products.py` uses `filter_product_for_public` in `_product_for_public_response`; `api/ucp.py` uses it in `_product_to_ucp_item`; `api/ucp_rpc.py` filters discovery/search and discovery/getProduct results.

### 5. RegistryDriver (Orchestrator)

- **Location:** `services/orchestrator-service/registry.py` — `AgentEntry(base_url, display_name, slug)`, `get_agents(capability=None)`, `get_capabilities()`.
- **Behavior:** Reads `internal_agent_registry` (Supabase), filters by capability and enabled; slug from `_display_name_to_slug(display_name)`. Fallback when DB empty: one entry from `settings.discovery_service_url` with slug `"discovery"`.

### 6. JSON-RPC 2.0 Discovery + Orchestrator client (Task 3.1)

- **Discovery:** `api/ucp_rpc.py` — `POST /api/v1/ucp/rpc`; methods `discovery/search` (scout_engine.search + filter_products_for_public) and `discovery/getProduct` (get_product_by_id + filter_product_for_public). Router registered in `main.py`.
- **Orchestrator:** `clients.py` — `discover_products_via_rpc(base_url, query, limit, ...)` POSTs JSON-RPC to `{base_url}/api/v1/ucp/rpc` with gateway signature when `GATEWAY_INTERNAL_SECRET` set.

### 7. Broadcast discovery with streaming (Task 2.2)

- **Location:** `services/orchestrator-service/clients.py` — `discover_products_broadcast(...)`.
- **Behavior:** Uses `get_agents(capability="discovery")`; fans out `discover_products_via_rpc` per agent with `asyncio.gather(return_exceptions=True)`; merges products (dedupe by id); returns same shape as `discover_products` (data, machine_readable, adaptive_card, metadata). Falls back to REST `discover_products` when no agents. Chat uses `discover_products_broadcast` as `discover_products_fn`.

### 8. ID masking at Gateway + TTL (Task 2.3)

- **Migration:** `supabase/migrations/20250128130000_id_masking_agent_slug_expires.sql` — `id_masking_map` gains `agent_slug TEXT`, `expires_at TIMESTAMPTZ`.
- **Orchestrator:** `config.py` — `ID_MASKING_ENABLED`, `ID_MASKING_TTL_HOURS`. `db.py` — `store_masked_id(agent_slug, internal_product_id, partner_id, source)` inserts into `id_masking_map` with `expires_at = now + TTL`, returns `uso_{agent_slug}_{short_uid}`.
- **Broadcast:** When `id_masking_enabled`, each product from each agent is masked via `store_masked_id(slug, id, partner_id, "rpc")` and `partner_id` stripped from response.
- **Discovery:** `resolve_masked_id()` selects `expires_at` and returns `None` if expired (expires_at in the past). Add-to-bundle and UCP checkout already resolve masked ids before DB.

### 9. Unified manifest from registry (Task 2.4)

- **Location:** `services/orchestrator-service/api/gateway_ucp.py`.
- **Behavior:** `GET /.well-known/ucp` built from `registry.get_capabilities()`; single `rest.endpoint` and `rest.schema` point to Gateway (`GATEWAY_PUBLIC_URL`). Capabilities default to `["discovery"]` when registry empty. Proxy routes `GET /api/v1/gateway/ucp/items`, `POST /api/v1/gateway/ucp/checkout`, `GET /api/v1/gateway/ucp/rest.openapi.json` forward to Discovery with `X-Gateway-Signature` when `GATEWAY_INTERNAL_SECRET` set.

### 10. Multi-Agent Discovery (encapsulation)

- Internal Business Agent uses experience_tags and product_capability_mappings internally; responses are UCP-shaped. Planner visibility: discover and get_product use `filter_product_for_public`; no experience_tags or internal schema exposed.

### 11. Experience-tag discovery and theme bundles

- Semantic/DB filter and boost, discover API, experience-categories endpoint, discover_composite theme picking, intent and tools schema — as documented in the checklist in the plan. All implemented.

---

## Optional / follow-ups

- **Frontend theme badge/picker:** Out of scope (API supports `experience_tag` / `experience_tags` on discover).
- **Cleanup job for expired id_masking_map rows:** Optional periodic delete where `expires_at < NOW()`.

---

## Deployment impact

| Service        | Changes                                                                 | Action                    |
|----------------|-------------------------------------------------------------------------|---------------------------|
| Discovery      | ucp_rpc, gateway_signature (UCP-only), semantic_search (match_products_v2), products/ucp/ucp_rpc (filter_products), db (resolve_masked_id TTL) | Restart; run new migrations |
| Orchestrator   | registry, clients (RPC + broadcast + masking), gateway_ucp (signing), config (id_masking, LLM), planner (facade), db (store_masked_id) | Restart; run new migrations |
| Intent         | No A2A-specific code changes                                            | Restart if using shared   |
| Supabase       | Migrations: match_products_v2, id_masking_map (agent_slug, expires_at)  | Apply migrations          |

**Env (Orchestrator):** `ID_MASKING_ENABLED`, `ID_MASKING_TTL_HOURS`, `GATEWAY_INTERNAL_SECRET`, `GATEWAY_PUBLIC_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (for registry + id_masking_map).  
**Env (Discovery):** `GATEWAY_INTERNAL_SECRET` (or `GATEWAY_SIGNATURE_REQUIRED` + secret) for UCP routes; `ID_MASKING_ENABLED` for local masking if used.
