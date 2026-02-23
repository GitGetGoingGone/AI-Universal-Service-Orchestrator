---
name: Experience-tag discovery and theme bundles
overview: Add experience-tag-based discovery (return tags from semantic search, filter and rank/boost by tag), expose experience categories to the model, and extend the composite flow so the model suggests 3-4 theme bundles (with experience_tags); products are matched to each bundle by experience_tag and users pick a theme then choose products within it.
todos: []
isProject: false
---

# Experience-tag discovery and theme bundles

## Current state

- **Discovery**: Products have `experience_tags` (JSONB); DB search returns them; aggregator `UCPProduct` and `to_dict()` include them. Semantic search does **not** return `experience_tags`; there is no filter or boost by tag.
- **Composite flow**: Intent returns `search_queries` (capability categories, e.g. flowers, restaurant, movies) and `bundle_options` (label, description, categories). `_discover_composite` calls `discover_products(query)` once per category, then builds 3-4 suggested bundles by picking one product per category per tier from the same pool. No theme/experience_tag in the loop.
- **Intent**: [services/intent-service/llm.py](services/intent-service/llm.py) `resolve_intent` uses a system prompt (from DB or `get_intent_system_prompt`) and returns `intent_type`, `search_queries`, `bundle_options`, etc. No experience categories or theme bundles today.

## Architecture (target flow)

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant Intent
    participant Discovery
    participant DB

    User->>Orchestrator: "Plan a romantic date night"
    Orchestrator->>Discovery: GET /experience-categories
    Discovery->>DB: distinct experience_tags
    DB-->>Discovery: ["romantic","luxury","celebration",...]
    Discovery-->>Orchestrator: experience_categories
    Orchestrator->>Intent: resolve_intent(text, experience_categories)
    Intent-->>Orchestrator: bundle_options with experience_tags per option
    Orchestrator->>Discovery: discover_composite(search_queries, bundle_options)
    loop Per category
        Orchestrator->>Discovery: discover_products(query, experience_tag?)
        Discovery->>DB: search + filter/boost by experience_tag
        DB-->>Discovery: products (with experience_tags)
        Discovery-->>Orchestrator: products
    end
    Orchestrator->>Orchestrator: Build suggested_bundle_options (pick best product per category per tier by experience_tags)
    Orchestrator-->>User: 3-4 theme bundles; user picks one, then refines products
```



## 1. Return experience_tags from semantic search

- **File**: [services/discovery-service/semantic_search.py](services/discovery-service/semantic_search.py)
- **Change**: The RPC `match_products` returns `SETOF products` (full row), so `experience_tags` is already in `r`. Add `"experience_tags"` to `select_cols` when building the returned list (lines 101-106) so the semantic path returns the same shape as DB search and includes `experience_tags`.
- **No migration**: RPC already returns full row; only Python normalization is updated.

## 2. Filter products by experience tag

- **Discovery API**
  - **File**: [services/discovery-service/api/products.py](services/discovery-service/api/products.py)
  - Add optional query param: `experience_tag: Optional[str] = Query(None)` (single tag; could later add `experience_tags: Optional[List[str]]` for OR). Pass to `search()`.
- **Scout engine**
  - **File**: [services/discovery-service/scout_engine.py](services/discovery-service/scout_engine.py)
  - Add `experience_tag: Optional[str] = None` to `search()` and `_fetch_and_rank()`; pass through to `_fetch_via_aggregator()` and to `search_products()` / `semantic_search()` when not using aggregator.
  - **File**: [services/discovery-service/db.py](services/discovery-service/db.py)
  - Add `experience_tag: Optional[str] = None` to `search_products()`. When set, filter with JSONB contains: Supabase Python client `.contains("experience_tags", [experience_tag])` (array containment). Use a single-element list so that rows where `experience_tags` contains that tag are returned.
- **Semantic path**
  - **New migration** (e.g. `supabase/migrations/YYYYMMDD_match_products_experience_tag.sql`): Alter `match_products` to add optional `filter_experience_tag text DEFAULT NULL`. In the `WHERE` clause add: `AND (filter_experience_tag IS NULL OR p.experience_tags ? filter_experience_tag)` (PostgreSQL `?` = key/element exists in JSONB).
  - **File**: [services/discovery-service/semantic_search.py](services/discovery-service/semantic_search.py)
  - Pass `filter_experience_tag` into the RPC kwargs when `experience_tag` is provided.
- **Aggregator**
  - **File**: [packages/shared/discovery_aggregator.py](packages/shared/discovery_aggregator.py)
  - Add `experience_tag: Optional[str] = None` to `LocalDBDriver.search()`, `DiscoveryAggregator.search()`, and the `_search` call inside `LocalDBDriver`. Pass through from scout engine when calling aggregator.
- **Orchestrator client**
  - **File**: [services/orchestrator-service/clients.py](services/orchestrator-service/clients.py)
  - Add `experience_tag: Optional[str] = None` to `discover_products()`; add to request params and pass to discovery service.

## 3. Rank/boost by experience tag

- **File**: [packages/shared/ranking.py](packages/shared/ranking.py)
  - Add optional `experience_tag_boost: Optional[str] = None` (and optionally `experience_tag_boost_amount: float = 0.2`) to `sort_products_by_rank()`. If `experience_tag_boost` is set, before sorting add a boost to the score for products whose `experience_tags` (list) contains that tag (e.g. `score += experience_tag_boost_amount`). Reuse the same `scored` loop or a second pass; keep sponsor boost logic unchanged.
  - Alternatively, add a small helper `apply_experience_tag_boost(products, experience_tag, amount)` that returns products with an extra `_rank_boost` or integrate into existing score computation in `sort_products_by_rank`.
- **File**: [services/discovery-service/scout_engine.py](services/discovery-service/scout_engine.py)
  - When `experience_tag` is provided, pass it into `_apply_ranking` (or the ranking config). Extend the ranking layer to accept an optional `experience_tag_boost` and pass it to `sort_products_by_rank`. So: `get_platform_config_ranking()` or a new param; the scout engine will need to pass `experience_tag` into the ranking call so that `sort_products_by_rank` can apply the boost.

Concrete wiring: add optional parameter `experience_tag: Optional[str] = None` to `_apply_ranking(..., experience_tag=None)`. Inside `_apply_ranking`, call `sort_products_by_rank(..., experience_tag_boost=experience_tag)`. In `sort_products_by_rank`, when `experience_tag_boost` is set, add a fixed boost to the score for products where `(product.get("experience_tags") or [])` contains that tag.

## 4. Experience-tag-based categories (list for the model)

- **New endpoint**: GET `/api/v1/experience-categories` (or `/discover/experience-categories`) in the discovery service.
  - **File**: [services/discovery-service/api/products.py](services/discovery-service/api/products.py) (or a small new router file if preferred)
  - Returns a list of distinct experience tag values from products (e.g. from a Supabase RPC or raw SQL). Options:
    - **Option A**: Supabase RPC `get_distinct_experience_tags()` that does `SELECT DISTINCT jsonb_array_elements_text(experience_tags) AS tag FROM products WHERE deleted_at IS NULL ORDER BY tag`. RPC returns `[{ "tag": "celebration" }, ...]`.
    - **Option B**: In discovery service, use a one-off query: e.g. `client.rpc("get_distinct_experience_tags")` or a direct `client.from_("products").select("experience_tags")` and flatten/dedup in Python (less efficient for large tables).
  - Prefer **Option A** with a new migration that creates `get_distinct_experience_tags() RETURNS SETOF text` (or table with one column).
  - Response shape: `{ "data": { "experience_categories": ["baby", "celebration", "gift", "luxury", "night out", "romantic", "travel"] } }`.
- **Orchestrator / intent**
  - When calling resolve_intent (or before planning), orchestrator can call discovery’s GET experience-categories and pass the list into the intent so the model knows “all available experience categories.” Alternatively, the intent service could call discovery internally; passing from orchestrator keeps intent stateless and lets the planner decide when to fetch categories.

## 5. Theme bundles: model suggests 3-4 bundles from experience categories; match products by theme

- **Intent**
  - **System prompt / DB prompt**: Extend the intent system prompt (and any DB-backed prompt for “intent”) to:
    - Include a line that the model will receive (or can assume) a list of **experience_categories** (e.g. romantic, luxury, celebration, night out, gift, baby).
    - For composite intents, ask the model to return 3-4 **theme** bundle options. Each option: `label`, `description`, `categories` (capability categories, e.g. flowers, restaurant, movies), and `**experience_tags**` (e.g. `["romantic"]` or `["luxury","celebration"]`) that define the theme.
  - **API contract**: Intent response already has `bundle_options: [{ label, description, categories }]`. Extend to `bundle_options: [{ label, description, categories, experience_tags }]`. Validate/normalize `experience_tags` as a list of strings (lowercase, trim).
- **Orchestrator**
  - **Resolve intent input**: When orchestrator calls resolve_intent, it can pass `experience_categories` (from GET experience-categories) in the payload or context so the intent LLM can use it. This may require extending the intent API and [services/intent-service/llm.py](services/intent-service/llm.py) to accept optional `experience_categories: List[str]` and inject it into the user or system message (e.g. “Available experience categories: romantic, luxury, celebration, …”).
  - **discover_composite**
    - **File**: [services/orchestrator-service/agentic/loop.py](services/orchestrator-service/agentic/loop.py)
    - **Option A (theme-scoped discovery)**: Add optional `theme_experience_tag: Optional[str] = None` to `_discover_composite` (from intent or first bundle option). When calling `discover_products_fn`, pass `experience_tag=theme_experience_tag` so all category fetches are filtered/boosted by that theme. Then when building `suggested_bundle_options`, for each option still pick one product per category (from the already theme-scoped pool); if options have different `experience_tags`, we could still sort within each category by how well the product matches each option’s `experience_tags` (see Option B).
    - **Option B (efficient: one fetch per category, then assign by theme)**: Do **not** pass experience_tag into discover_products (or pass only when we want a single global theme). After building `category_products` (one product list per category), when building each of the 3-4 `suggested_bundle_options`, for each option use that option’s `experience_tags`: for each category, sort `_get_products_for_category(cat)` by “best match” to option’s experience_tags (e.g. products that have any of the option’s experience_tags get a boost; pick first). Implement a small helper e.g. `_pick_best_product_for_theme(products, experience_tags)` that sorts by number of matching tags (or boolean match) and returns the first product. This avoids N×M discover calls and uses the existing category_products.
  - **Recommendation**: Implement **Option B** first (one discover per category; then when building suggested_bundle_options, for each option and each category, choose the best product by experience_tags match). Optionally add **Option A** later (e.g. when intent sets a single `theme_experience_tag` for the whole composite, pass it to discover_products for filter+boost).
  - **Tool and execute_tool**: [services/orchestrator-service/agentic/tools.py](services/orchestrator-service/agentic/tools.py) — extend `discover_composite` tool schema to include optional `theme_experience_tag` and ensure `bundle_options` items can carry `experience_tags`. Guardrails: allow `experience_tags` in each bundle option when present.
- **Suggested bundle option shape**
  - Keep existing fields: `label`, `description`, `product_ids`, `product_names`, `total_price`, `currency`, `categories`. Add optional `experience_tags: ["romantic"]` to each suggested option so the frontend can show theme. When building suggested_bundle_options in `_discover_composite`, copy `experience_tags` from the intent bundle option into the suggested option.
- **Frontend / “pick theme then pick products”**
  - Current flow already shows suggested_bundle_options and lets user pick a bundle; refine_bundle_category allows swapping a product within a category. No change strictly required for “pick theme then pick products” except ensuring suggested_bundle_options are rendered with theme labels and that refine_bundle_category (or equivalent) continues to work. If the frontend should “filter by selected theme” when showing alternatives, that can be a follow-up (e.g. passing selected bundle’s experience_tags when calling refine_bundle_category or discover_products for that category).

## 6. End-to-end wiring

- **Orchestrator flow**
  - Before or during the first planning iteration, fetch experience categories (GET discovery experience-categories). Pass them into resolve_intent (extend intent API if needed).
  - Intent returns `bundle_options` with `experience_tags` per option.
  - When calling discover_composite, pass `search_queries`, `bundle_options` (with experience_tags). Optionally pass a single `theme_experience_tag` if intent sets it.
  - _discover_composite: for each category call discover_products(query, …, experience_tag=theme_experience_tag if desired). Build suggested_bundle_options; for each option, for each category, pick best product by option’s experience_tags (sort category list by tag match, take first). Attach option’s experience_tags to suggested_bundle_options for the client.

## File checklist (implementation order)


| #   | Area                      | File(s)                                                                                    | Change                                                                                                                                                   |
| --- | ------------------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Semantic return           | [semantic_search.py](services/discovery-service/semantic_search.py)                        | Add `experience_tags` to returned dict                                                                                                                   |
| 2   | DB filter                 | [db.py](services/discovery-service/db.py)                                                  | Add `experience_tag` param; filter with `.contains("experience_tags", [tag])`                                                                            |
| 3   | Semantic RPC              | New migration                                                                              | `match_products` add `filter_experience_tag`; WHERE with `experience_tags ? filter_experience_tag`                                                       |
| 4   | Semantic call             | [semantic_search.py](services/discovery-service/semantic_search.py)                        | Pass `filter_experience_tag` to RPC                                                                                                                      |
| 5   | Aggregator                | [discovery_aggregator.py](packages/shared/discovery_aggregator.py)                         | Add `experience_tag` to LocalDBDriver and DiscoveryAggregator.search                                                                                     |
| 6   | Scout                     | [scout_engine.py](services/discovery-service/scout_engine.py)                              | Add `experience_tag` to search, _fetch_and_rank, _fetch_via_aggregator; pass to ranking                                                                  |
| 7   | Ranking                   | [ranking.py](packages/shared/ranking.py)                                                   | Add experience_tag_boost to sort_products_by_rank                                                                                                        |
| 8   | Discover API              | [api/products.py](services/discovery-service/api/products.py)                              | Add `experience_tag` query param; pass to search()                                                                                                       |
| 9   | Experience-categories API | New RPC + [api/products.py](services/discovery-service/api/products.py) or router          | GET /experience-categories using RPC get_distinct_experience_tags                                                                                        |
| 10  | Orchestrator client       | [clients.py](services/orchestrator-service/clients.py)                                     | Add `experience_tag` to discover_products                                                                                                                |
| 11  | discover_composite        | [loop.py](services/orchestrator-service/agentic/loop.py)                                   | Build suggested_bundle_options by picking best product per category per option by experience_tags; optional theme_experience_tag to discover_products_fn |
| 12  | Intent prompt + API       | Intent system prompt (and DB prompt); [llm.py](services/intent-service/llm.py); intent API | Document experience_categories; return bundle_options with experience_tags; accept experience_categories in resolve_intent                               |
| 13  | Tools                     | [tools.py](services/orchestrator-service/agentic/tools.py)                                 | discover_composite: allow experience_tags in bundle_options; optional theme_experience_tag                                                               |


## Out of scope / follow-ups

- Multiple experience_tags filter (OR/AND) in one request.
- Frontend UI changes for “theme” badge or filtering by selected theme in refine flow.
- Persisting “selected theme bundle” in state for multi-turn refinement (current state already keeps suggested_bundle_options and last selection).

