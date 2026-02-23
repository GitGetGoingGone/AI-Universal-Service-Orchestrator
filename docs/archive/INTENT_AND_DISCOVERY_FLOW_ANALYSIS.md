# Intent and Discovery Flow – Use Case Analysis

This document provides a thorough analysis of the intent resolution and product discovery flow across the USO platform. It lists all use cases, current behavior, and handling recommendations.

---

## 1. High-Level Architecture

```
User Message → Chat API → Orchestrator
                              ↓
                    run_agentic_loop (or _direct_flow)
                              ↓
                    plan_next_action (Planner LLM)
                              ↓
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
       resolve_intent   discover_products   discover_composite
              ↓               ↓               ↓
       Intent Service   Discovery Service   (orchestrator calls
       (LLM or          (scout_engine      discover_products
        heuristics)       search)            per category)
```

---

## 2. Intent Resolution

### 2.1 Entry Points

| Entry | Location | When Used |
|-------|----------|-----------|
| Intent Service API | `services/intent-service/api/resolve.py` | Direct `/api/v1/resolve` calls |
| Orchestrator | `services/orchestrator-service/clients.py` → `resolve_intent()` | Called by agentic loop via `resolve_intent_fn` |
| Orchestrator fallback | `services/intent-service/llm.py` | When Intent service unavailable (uses local `resolve_intent`) |

### 2.2 Resolution Paths

| Path | Condition | Output |
|------|-----------|--------|
| **LLM** | `llm_config` + `api_key` + prompt enabled | Parsed JSON from model |
| **Heuristics** | LLM unavailable, or `force_model=False` and LLM failed | `_heuristic_resolve()` |
| **Force model** | `force_model=True` (ChatGPT/Gemini) | LLM only; no heuristic fallback on failure |

### 2.2a Intent-First (Orchestrator Loop)

- **Every user message**: Intent is called first with full context (`last_suggestion`, `recent_conversation`, `probe_count`, `thread_context`).
- **recommended_next_action**: Intent returns one of `discover_composite`, `discover_products`, `complete_with_probing`, `handle_unrelated`, `complete`.
- **Loop**: Uses `recommended_next_action` when present to decide next step (iteration 0). Planner still used for message generation (probing, handle_unrelated).

### 2.3 Intent Types

| Intent | Description | Key Fields |
|--------|-------------|------------|
| `discover` | Single product category | `search_query`, `entities` |
| `discover_composite` | Composed experience (date night, birthday, picnic) | `search_queries`, `experience_name`, `entities` |
| `browse` | Generic exploration | `search_query` often empty |
| `checkout` | Payment/checkout | — |
| `track` | Order status | — |
| `support` | Help/complaint/refund | — |

### 2.4 Heuristic Rules (Intent Service)

| User Input | Intent | Notes |
|------------|--------|-------|
| Empty, "hi", "hello", "hey", "help" | `browse` | |
| "checkout", "pay", "payment", "order" | `checkout` | |
| "track", "status", "where is", "shipped" | `track` | |
| "support", "help", "complaint", "refund" | `support` | |
| `last_suggestion` has probe keywords + user answers with details | `discover_composite` | Uses `["flowers","dinner","movies"]`, `experience_name="date night"` |
| "date night", "plan a date" | `discover_composite` | `search_queries=["flowers","dinner","movies"]` |
| "birthday party", "birthday celebration" | `discover_composite` | `search_queries=["cake","flowers","gifts"]` |
| "picnic" | `discover_composite` | `search_queries=["basket","blanket","food"]` |
| "gift" in message | `discover` | `search_query="gifts"` |
| Budget phrase ("under $50") | `discover` | `entities: [{type:"budget", value:5000}]` |
| Default | `discover` | `search_query` from `derive_search_query(text)` or "browse" |

### 2.5 LLM Intent Prompt Rules (from `intent_system.txt`)

- `discover_composite` for date night, birthday party, picnic.
- When `last_suggestion` has probing questions and user answers (date, budget, preferences): stay in `discover_composite`, do not use answer as `search_query`.
- When `last_suggestion` exists and user refines (e.g. "no flowers, add movie"): update `search_queries`.

---

## 3. Planner (Agentic Loop)

### 3.1 Flow

1. **Iteration 0**: Planner receives user message + state (messages, probe_count, thread_context).
2. Planner chooses: `resolve_intent` | `discover_products` | `discover_composite` | `complete` | other tools.
3. Tool runs; result stored in `state["last_tool_result"]`.
4. Loop continues until `complete` or max iterations.

### 3.2 Planner Rules (from `PLANNER_SYSTEM`)

| Scenario | Expected Action |
|----------|-----------------|
| New message | First call `resolve_intent` |
| Intent `discover`, generic message | Prefer probing; `complete` with questions |
| Intent `discover`, user has details | Call `discover_products` |
| Intent `discover_composite`, generic | Prefer probing; `complete` with questions |
| Intent `discover_composite`, user has details | Call `discover_composite` |
| `last_suggestion` shows probing + user answered | Must fetch products (resolve_intent → discover) |
| `last_suggestion` + user refines | Use updated `search_queries` from intent |
| Intent checkout/track/support | Use `track_order` when thread has `order_id` |
| `probe_count >= 2` | Proceed with assumptions, call discover |
| Composite + location | Call `get_weather`, `get_upcoming_occasions` before discover/complete; use to suggest optimal dates |

### 3.3 Loop Overrides

| Condition | Override |
|-----------|----------|
| Planner says "Done."/empty, no products, `last_suggestion` has probe keywords | Force `resolve_intent` |
| `probe_count >= 2`, planner wants to probe again | Force `discover_composite` (or discover_products) with assumptions |
| Planner returns `complete` with message | Use that message; break |

### 3.4 Fallback Plan (No LLM)

- Iteration 0: `resolve_intent`
- Iteration 1: Based on intent:
  - `discover` + `search_query`: `discover_products`
  - `discover_composite` without details: `complete` with probing message
  - `discover_composite` with details: `discover_composite`
- Iteration ≥ 2 with products: `complete` with empty message (engagement response)
- Else: `complete` with "Processed your request."

### 3.5 External Factors (Weather, Events)

The planner **always** checks external factors when the user provides or implies a location for composite experiences (date night, picnic, etc.):

| When | Tools to Call | Purpose |
|------|---------------|---------|
| User has location | `get_weather`, `get_upcoming_occasions` | Current weather and local events |
| User gives flexible date ("anytime next week", "this weekend") | `web_search` with "weather forecast [location] [timeframe]" | Multi-day outlook for date suggestions |

**Expected behavior**: Use the data to suggest optimal dates in the response. Examples:
- "Wednesday looks best for outdoor plans—clear skies."
- "Avoid Friday near downtown due to the football game crowd."
- "Thursday and Saturday have the nicest weather next week."

Requires external APIs configured in Platform Config (weather, events, web_search). If not configured, tools return an error and the planner proceeds without external context.

### 3.6 Upsell & Surge Rules Layer

After intent resolution, the rules layer (`agentic/rules.py`) evaluates `platform_config.upsell_surge_rules`:

- **Upsell rules**: Add-on categories to suggest (e.g. card, chocolates for gifts).
- **Surge rules**: Apply surge pricing when urgency signals match.
- **Promo rules**: Suggest products at discount when added before checkout (`trigger: before_checkout`, `min_bundle_items`).

Output (`addon_categories`, `apply_surge`, `surge_pct`, `promo_products`) is passed to engagement context. Configurable in Platform Config → Discovery → Upsell & Surge Rules.

---

## 4. Discovery Flow

### 4.1 discover_products

| Component | Behavior |
|-----------|----------|
| **Orchestrator** | Calls `discover_products_fn(query, limit, location, budget_max)` |
| **Discovery API** | `GET /api/v1/discover?intent={query}&limit=...` |
| **scout_engine.search** | Semantic or text search; browse query → sample products |
| **Returns** | `{ data: { products, count }, adaptive_card, machine_readable }` |

### 4.2 discover_composite

| Step | Behavior |
|------|----------|
| 1 | For each `search_query` in `search_queries`, call `discover_products_fn` |
| 2 | Build `categories: [{ query, products }]` |
| 3 | Generate experience card |
| 4 | Optionally run `suggest_composite_bundle_options` or `suggest_composite_bundle` |

### 4.3 Scout Engine Search

| Query | Behavior |
|-------|----------|
| Empty | `_fetch_and_rank("", limit, ...)` – sample products |
| Browse terms ("show", "browse", "products", etc.) | Same as empty |
| Multi-word | `derive_search_query()` strips action words |
| Semantic available | Try pgvector; fallback to text if no results |

---

## 5. Use Cases and Current Behavior

### 5.1 "Plan a date night" (generic)

| Step | What Happens |
|------|--------------|
| 1 | User: "Plan a date night" |
| 2 | `resolve_intent` → `discover_composite`, `search_queries=["flowers","dinner","movies"]` |
| 3 | Planner: probing preferred → `complete` with questions |
| 4 | User sees: "What date? Budget? Dietary preferences? Location?" |

**Status**: Working as designed.

---

### 5.2 User answers probing (e.g. "this weekend, $100")

| Step | What Happens |
|------|--------------|
| 1 | User: "this weekend, $100" |
| 2 | `resolve_intent` with `last_suggestion` = probing text |
| 3 | Heuristic: `is_answer` true → `discover_composite` |
| 4 | Planner: should call `discover_composite` |
| 5 | `discover_composite` runs for flowers, dinner, movies |
| 6 | Products returned (or empty if catalog has none) |

**Status**: Works when heuristic/LLM correctly treats as answer. Override in loop handles "Done." when `last_suggestion` has probe keywords.

---

### 5.3 "Show me more options"

| Step | What Happens |
|------|--------------|
| 1 | User: "Show me more options" (after probing) |
| 2 | `resolve_intent` with `last_suggestion` = probing questions |
| 3 | Heuristic: "show me" is in `detail_indicators` exclusion: `text_lower.startswith("show me")` → `is_answer` = false |
| 4 | Falls through to default → `discover` with `search_query` from `derive_search_query("show me more options")` |
| 5 | `derive_search_query`: strips "show", "me" → keeps "more", "options" |
| 6 | `search_query` = "more options" |
| 7 | Planner: may call `discover_products` with query "more options" |
| 8 | Discovery: search for "more options" → likely no products |
| 9 | Planner: may `complete` with "Processed your request." |

**Root cause**: "Show me more options" is not treated as a refinement of the date night flow. Intent becomes `discover` with a poor query, and discovery returns nothing.

**Fix**: Treat "show me more options", "more options", "other options" after composite probing as `discover_composite` with same `search_queries` (or as explicit "fetch products" signal).

---

### 5.4 "Show me chocolates"

| Step | What Happens |
|------|--------------|
| 1 | `resolve_intent` → `discover`, `search_query` = "chocolates" |
| 2 | Planner: may probe or fetch |
| 3 | If fetch: `discover_products("chocolates")` |
| 4 | Discovery returns chocolate products |

**Status**: Works when planner fetches.

---

### 5.5 "I don't want flowers, add a movie"

| Step | What Happens |
|------|--------------|
| 1 | `resolve_intent` with `last_suggestion` (had flowers) |
| 2 | LLM/heuristic should return `discover_composite` with updated `search_queries` |
| 3 | Planner calls `discover_composite` with new queries |
| 4 | Products returned |

**Status**: Depends on intent correctly interpreting refinement.

---

### 5.6 Browse / "Hi", "Show me something"

| Step | What Happens |
|------|--------------|
| 1 | `resolve_intent` → `browse` or `discover` with empty/browse query |
| 2 | Planner: may `complete` with engagement |
| 3 | If discover: `discover_products("")` or `discover_products("browse")` → sample products |

**Status**: Works when discovery handles browse.

---

### 5.7 "What's my order status?" (with thread order_id)

| Step | What Happens |
|------|--------------|
| 1 | `resolve_intent` → `track` |
| 2 | Planner: `track_order` with `order_id` from `thread_context` |
| 3 | Order status returned, summarized for user |

**Status**: Implemented with thread context.

---

### 5.8 probe_count >= 2

| Step | What Happens |
|------|--------------|
| 1 | After 2+ probing rounds, planner wants to probe again |
| 2 | Loop override: force `discover_composite` with assumptions |
| 3 | Products fetched with default queries |

**Status**: Implemented.

---

### 5.9 Discovery returns no products

| Step | What Happens |
|------|--------------|
| 1 | `discover_products` or `discover_composite` returns `products: []` |
| 2 | `products_data` has empty products |
| 3 | `generate_engagement_response` builds context with empty product list |
| 4 | User may see "No products found" or generic message |

**Status**: Depends on engagement prompt and catalog. Empty catalog → no products regardless of intent.

---

## 6. Edge Cases and Gaps

| Case | Current Behavior | Recommendation |
|------|-------------------|----------------|
| "Show me more options" after probing | Treated as `discover` with "more options" → no products | Add heuristic: after composite probing, treat as "fetch products" / `discover_composite` |
| "More options", "Other options", "Different options" | Same as above | Same |
| "Just show me something" | May get browse or poor query | Ensure browse path returns sample products |
| Intent service down | Heuristics used | Already handled |
| LLM returns invalid JSON | Heuristics used (unless `force_model`) | Already handled |
| Discovery 429 | Retry then empty fallback | Already handled |
| Empty catalog | No products for any query | Document; consider fallback messaging |
| Planner completes with "Done." when user answered | Override forces `resolve_intent` | Already handled |
| `discover_composite` with empty `search_queries` | May error or return nothing | Validate and default to `["flowers","dinner","movies"]` for date night |

---

## 7. Summary: "Show me more options" Bug

**Flow**:
1. User: "Plan a date night" → probing
2. User: "Show me more options"
3. Intent: `discover`, `search_query` = "more options" (or similar)
4. Planner: `discover_products("more options")` or `complete`
5. Discovery: no products for "more options"
6. User sees: "Processed your request." / "No products found"

**Implemented fix**:
1. **Intent heuristic** (`llm.py`): When `last_suggestion` has probe keywords and user says "show more options", "more options", "other options", etc., return `discover_composite` with `unrelated_to_probing: true`.
2. **Intent prompt**: Rule added for unrelated response → return `discover_composite` with `unrelated_to_probing: true`.
3. **Planner**: When intent has `unrelated_to_probing`, call complete with a graceful message (rephrase question or offer to proceed with assumptions). Fallback message in loop when planner returns "Done.".
4. **Assumptions**: When we don't have date/dietary info, assume today/tomorrow and no dietary constraints. Proceed with `discover_composite` after 2+ probes.

---

## 8. File Reference

| Component | File |
|-----------|------|
| Intent resolution (LLM + heuristics) | `services/intent-service/llm.py` |
| Intent API | `services/intent-service/api/resolve.py` |
| Intent prompt | `packages/shared/prompts/intent_system.txt` |
| Planner | `services/orchestrator-service/agentic/planner.py` |
| Agentic loop | `services/orchestrator-service/agentic/loop.py` |
| Tools | `services/orchestrator-service/agentic/tools.py` |
| Discovery client | `services/orchestrator-service/clients.py` |
| Discovery API | `services/discovery-service/api/products.py` |
| Scout engine | `services/discovery-service/scout_engine.py` |
| Shared discovery utils | `packages/shared/discovery.py` |
| Engagement response | `services/orchestrator-service/agentic/response.py` |
