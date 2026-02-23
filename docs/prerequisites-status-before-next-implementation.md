# Prerequisites Before Next Implementation — Status Report

Status of each prerequisite for semantic/KB search and distributed Business Agent (A2A) flows.

---

## 1. Vector database support (pgvector)

| Item | Status | Notes |
|------|--------|--------|
| pgvector extension | **Done** | `supabase/migrations/20240128000000_extensions.sql`: `CREATE EXTENSION IF NOT EXISTS vector;` |
| Products embedding column | **Done** | `products.embedding VECTOR(1536)` in `20240128000001_core_and_scout.sql` |
| Similarity search RPC | **Done** | `match_products(query_embedding, match_count, match_threshold, ...)` in `20240128000011_scout_semantic_search.sql` and `20250128000037_match_products_experience_tag.sql`; ivfflat index on `products.embedding` |
| Discovery usage | **Done** | `services/discovery-service/semantic_search.py`: `semantic_search()` calls RPC; Scout can use `use_semantic=True` (pgvector first, text fallback) |

**Verdict:** Ready. Supabase/PostgreSQL has pgvector; semantic search path exists and is used when embeddings are present.

---

## 2. Embedding provider

| Item | Status | Notes |
|------|--------|--------|
| Env / config | **Done** | `services/discovery-service/config.py`: `EMBEDDING_PROVIDER` (openai \| azure), `EMBEDDING_MODEL` / `EMBEDDING_DEPLOYMENT`, `OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`. Default provider is `azure` for backward compatibility. |
| Query embedding | **Done** | `semantic_search.get_query_embedding(text)` calls OpenAI or Azure embeddings API; returns 1536-dim vector (truncated if longer). |
| Backfill | **Done** | `backfill_product_embedding(product_id)` and `backfill_all_product_embeddings(limit)`; admin `POST /api/v1/admin/embeddings/backfill` supports single `product_id` or batch (omit `product_id`, optional `limit`). |

**Env vars (discovery service):**

- **Azure (default):** `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `EMBEDDING_MODEL` or `EMBEDDING_DEPLOYMENT` (e.g. `text-embedding-ada-002`, `text-embedding-3-small`).
- **OpenAI:** Set `EMBEDDING_PROVIDER=openai`, `OPENAI_API_KEY`, and `EMBEDDING_MODEL` (e.g. `text-embedding-3-small`). Dimension must be 1536 (or truncation is applied).

**Verdict:** Ready. Configure one provider and run backfill so products have embeddings; then semantic search will return results.

---

## 3. Semantic enrichment (Knowledge Base for products)

| Item | Status | Notes |
|------|--------|--------|
| Product fields today | **Done** | `products` has `name`, `description`, `capabilities`; `_get_product_embedding_input()` uses name + description + **description_kb** + capabilities. |
| `description_kb` | **Done** | Column `products.description_kb` added in `supabase/migrations/20250128100003_products_description_kb.sql`. Optional TEXT for “best used for”, use cases, FAQs; included in product embedding. |
| Partner Knowledge Base | **Exists** | Partner-facing KB articles exist for support/FAQs, not for product semantic enrichment. |

**Verdict:** Ready. Populate `description_kb` on products (e.g. from CMS or admin) for richer semantic search; backfill will include it in embeddings.

---

## 4. Shared security secret (GATEWAY_INTERNAL_SECRET)

| Item | Status | Notes |
|------|--------|--------|
| Config | **Done** | `services/discovery-service/config.py` and `services/orchestrator-service/config.py`: `gateway_internal_secret: str = get_env("GATEWAY_INTERNAL_SECRET") or ""`. |
| Signing (Orchestrator → Discovery) | **Done** | `packages/shared/gateway_signature.py`: `sign_request(method, path, body, secret)`; `orchestrator-service/clients.py` → `_gateway_headers_for_discovery()` adds `X-Gateway-Signature` and `X-Gateway-Timestamp` when `GATEWAY_INTERNAL_SECRET` is set. |
| Verification (Discovery) | **Done** | `services/discovery-service/middleware/gateway_signature.py`: verifies HMAC-SHA256 (method, path, body, timestamp); 5‑minute replay window. Enabled when `GATEWAY_SIGNATURE_REQUIRED=true` and `GATEWAY_INTERNAL_SECRET` is set. |

**Verdict:** Ready. Set the same `GATEWAY_INTERNAL_SECRET` in `.env` (or env) for both Orchestrator and Discovery (and any other Business Agent that must verify the gateway). Enable verification on Discovery with `GATEWAY_SIGNATURE_REQUIRED=true`.

---

## 5. Service registry (Business Agent URLs)

| Item | Status | Notes |
|------|--------|--------|
| JSON config file | **Not used** | There is no private JSON file in the repo that lists Business Agent internal URLs. |
| DB-backed registry | **Done** | Table `internal_agent_registry` (`capability`, `base_url`, `display_name`, `enabled`); migration `supabase/migrations/20250128100000_internal_agent_registry.sql`. |
| Lookup | **Done** | `services/discovery-service/db.py`: `get_internal_agent_urls(capability?)` returns enabled `base_url` values. |
| Usage | **Done** | Scout `_fetch_via_aggregator` uses `get_internal_agent_urls()`; when non-empty, builds UCPManifestDriver and queries internal agents in parallel with LocalDB. |

**Verdict:** Ready, but registry is **DB-based**, not a JSON file. To register a Business Agent (e.g. `http://discovery-service:8000/api/v1/ucp` or another internal agent), insert rows into `internal_agent_registry` (capability, base_url, display_name, enabled). If you specifically want a **Service Registry JSON** file for ops or deployment, that would be an additional artifact (e.g. generated from DB or used to seed DB).

---

## Summary

| Prerequisite | Status | Action before next implementation |
|--------------|--------|-----------------------------------|
| Vector DB (pgvector) | **Done** | None. |
| Embedding provider | **Done** | Set Azure or OpenAI env vars; run `POST /api/v1/admin/embeddings/backfill` (with or without `product_id`) to backfill. |
| Semantic enrichment (KB for products) | **Done** | Run migration `20250128100003_products_description_kb.sql`; optionally populate `description_kb` and re-backfill embeddings. |
| Shared secret (GATEWAY_INTERNAL_SECRET) | **Done** | Set same secret in Orchestrator and Business Agents; set `GATEWAY_SIGNATURE_REQUIRED=true` where verification is required. |
| Service registry | **Done** (DB) | Populate `internal_agent_registry` with Business Agent base URLs. Add a JSON registry file only if you need one for tooling/deployment. |

---

*Generated from codebase scan. Last updated: 2025-01-28.*
