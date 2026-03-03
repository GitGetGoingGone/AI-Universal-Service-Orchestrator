# Model Interactions Architecture

**Document Version:** 1.0  
**Date:** January 28, 2025  
**Audience:** Solution Architects, Technical Reviewers

This document describes the current model interactions, intent resolution, discovery flow, and agentic loop implementation for the AI Universal Service Orchestrator. It is intended for architect review of the intent, discovery, and model interaction design.

---

## 1. Overview

The platform uses multiple LLM interactions to power a conversational shopping experience:

1. **Intent** – Classifies user messages into structured intents (discover, discover_composite, browse, checkout, track, support, refine_composite).
2. **Planner** – Agentic decision engine that chooses the next tool to call based on state.
3. **Engagement** – Generates user-facing responses (curated listings, probing questions, concierge narratives).
4. **Suggest Composite Bundle** – Curates 2–4 bundle options from product categories for composite experiences.

All prompts are configurable via `model_interaction_prompts` in the database. Code defaults live in `packages/shared/prompts/` and service modules.

---

## 2. Model Interaction Types

| interaction_type | Display Name | When Used | Default max_tokens |
|------------------|--------------|-----------|--------------------|
| `intent` | Intent Resolution | First step when user sends a message; classifies what they want | 500 |
| `planner` | Agentic Planner | After each tool execution; decides next action | 500 |
| `engagement_discover` | Engagement: Discover | After discover_products returns results | 300 |
| `engagement_discover_composite` | Engagement: Composite | After discover_composite returns results | 800 |
| `engagement_browse` | Engagement: Browse | After loop completes with intent=browse | 150 |
| `engagement_default` | Engagement: Default | Checkout, track, support intents | 150 |
| `suggest_composite_bundle` | Bundle Curation (Composite) | When discover_composite returns products; suggests 2–4 bundle options | 500 |

---

## 3. Intent Resolution

### 3.1 Flow

```
User message → resolve_intent(text, last_suggestion, recent_conversation, probe_count, thread_context)
                    │
                    ├─ LLM path (when Platform Config has active_llm_provider + api_key + intent prompt enabled)
                    │       → model_interaction_prompts.system_prompt (intent)
                    │       → Returns JSON: intent_type, search_query, entities, bundle_options, etc.
                    │
                    └─ Heuristic path (fallback when LLM unavailable or disabled)
                            → Pattern matching, keyword rules, derive_search_query()
```

### 3.2 LLM vs Heuristics

**LLM is used when:**
- Supabase is configured
- `platform_config.active_llm_provider_id` points to a provider with `api_key`
- `model_interaction_prompts` has intent prompt `enabled = true`

**Heuristics are used when:**
- Supabase not configured
- No LLM config or missing api_key
- Intent prompt disabled in Model Interactions
- LLM call fails or returns unparseable JSON

### 3.3 Intent Types

| intent_type | Description | recommended_next_action |
|-------------|-------------|-------------------------|
| `discover` | Single product category (flowers, chocolates, baby items) | `discover_products` or `complete_with_probing` |
| `discover_composite` | Composed experience (date night, baby shower, birthday party) | `discover_composite` or `complete_with_probing` |
| `refine_composite` | Change a category in existing bundle (requires bundle_id) | `refine_bundle_category` |
| `browse` | Generic "show me products" with no specific query | `complete_with_probing` |
| `checkout` | Payment, checkout | `complete` |
| `track` | Order status, tracking | `complete` (often triggers track_order) |
| `support` | Help, complaint, refund | `complete` |

### 3.4 Heuristic Rules (Fallback)

- **browse**: "hi", "hello", "what items you got", "what do you have", "show me what you have", etc.
- **discover "X bundles/items"**: Extract primary category (e.g. "baby bundles" → search_query="baby"); qualifiers (bundles, items, products) are stripped.
- **refine_composite**: Requires `thread_context.bundle_id`; phrases like "change the flowers", "different chocolates".
- **discover_composite**: "plan a date night", "birthday party", "gift bundle"; probing follow-up when last_suggestion contains probe keywords.
- **Topic change**: "actually", "forget that", "never mind" → ignore last_suggestion, treat as fresh intent.
- **unrelated_to_probing**: User says "show more options" instead of answering probing questions → `unrelated_to_probing: true`.

---

## 4. Discovery Model

### 4.1 Search Logic

Discovery uses `search_products()` in `services/discovery-service/db.py`:

- **Browse queries**: `browse`, `show`, `what`, `products`, etc. → no text filter; returns sample products.
- **Category terms**: Qualifiers (`bundles`, `items`, `products`, `stuff`, `things`) are stripped.
- **Single term**: `ILIKE '%term%'` on name and description.
- **Multi-term**: AND logic – each category term must match (name OR description). E.g. "baby bundles" → intent extracts "baby" → single term search; if "newborn baby" → both terms required.

### 4.2 Browse Detection

`packages/shared/discovery.py`:

- `BROWSE_QUERIES`: sample, demo, show, browse, products, items, what, catalog, etc.
- `is_browse_query(query)` → True if query is in set or empty.
- `derive_search_query(text)` → strips action/filler words to get product terms.

### 4.3 Action/Filler Words (Stripped)

`_ACTION_FILLER_WORDS`: i, me, my, want, wanna, need, looking, for, find, get, book, show, please, the, a, an, to, for, service, help, like, would, could, can, what, you, got, items, etc.

---

## 5. Agentic Loop

### 5.1 High-Level Flow

```
User message
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Iteration 0: Intent-first                                        │
│   resolve_intent() → intent_data                                 │
│   Rules layer: upsell_surge, promo                               │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ recommended_next_action bypass (when applicable)                  │
│   discover_composite | discover_products | refine_bundle_category │
│   → Skip planner, call tool directly                             │
└─────────────────────────────────────────────────────────────────┘
    │ (else)
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ plan_next_action() → planner LLM                                  │
│   Input: state (messages, last_tool_result, last_suggestion,      │
│          probe_count, thread_context)                             │
│   Output: { action: "tool" | "complete", tool_name, tool_args }   │
└─────────────────────────────────────────────────────────────────┘
    │
    ├─ action = "complete" → break; generate engagement response
    │
    └─ action = "tool" → execute_tool() → update state → next iteration
```

### 5.2 State

```python
state = {
    "messages": [...],           # Conversation history
    "last_suggestion": str,      # Last assistant message (for refinement/probing context)
    "probe_count": int,         # Number of probing rounds
    "last_tool_result": {...},   # Result of last tool call
    "iteration": int,
    "agent_reasoning": [...],
    "bundle_id": str | None,
    "order_id": str | None,
}
```

### 5.3 Tools Available to Planner

| Tool | Description |
|------|-------------|
| `resolve_intent` | Resolve user message to structured intent |
| `discover_products` | Search products by query |
| `discover_composite` | Fetch products for composed experience; build bundle options |
| `refine_bundle_category` | Replace a category in existing bundle |
| `track_order` | Get order status |
| `get_weather` | Weather for location |
| `get_upcoming_occasions` | Events for location |
| `web_search` | Web search (e.g. weather forecast, ideas) |
| `create_standing_intent` | Standing intent with approval |
| `start_orchestration` | Long-running workflow |
| `complete` | Finish and return response to user |

### 5.4 Bypass Logic

When `recommended_next_action` is set by intent and not generic:

- `discover_composite` → call discover_composite with bundle_options, search_queries, experience_name
- `discover_products` → call discover_products with search_query (skip if query is generic like "browse")
- `refine_bundle_category` → call refine_bundle_category when bundle_id and category_to_change present

### 5.5 Special Overrides

- **unrelated_to_probing**: Planner must not return "Done."; use graceful message (rephrase or offer assumptions).
- **probe_count >= 2**: Proceed with discover_composite using assumptions (today/tomorrow, no dietary constraints) instead of probing again.
- **User answered probing**: If last_suggestion has probe keywords and user message looks like an answer, fetch products instead of completing.

---

## 6. Direct Flow (Non-Agentic)

When `use_agentic=False` or planner unavailable:

```
User message → resolve_intent() → intent_data
    │
    ├─ discover_composite → _discover_composite(search_queries, experience_name, ...)
    └─ discover → discover_products(query, limit, location)
    │
    ▼
_build_response() → adaptive_card, engagement
```

---

## 7. Full Prompts

### 7.1 Intent (`intent_system.txt`)

**Source:** `packages/shared/prompts/intent_system.txt`  
**DB override:** `model_interaction_prompts` where `interaction_type = 'intent'`

```
You are an intent classifier for a multi-vendor order platform.
Given a user message, extract:
1. intent_type: one of "discover", "discover_composite", "refine_composite", "checkout", "track", "support", "browse"
2. search_query: the product/category to search for (only for discover intent). Use 1-3 key terms. If unclear, use empty string.
3. For discover_composite: experience_name (e.g. "date night", "baby shower") and bundle_options (array of bundle tiers)
4. entities: list of {type, value} e.g. [{"type":"location","value":"NYC"}]. For composite experiences, also extract fulfillment when user provides: pickup_time (e.g. "6 PM", "6:00", "tonight"), pickup_address (street address for pickup), delivery_address (where to deliver, e.g. restaurant name or address).

Rules:
- "discover" = user wants to find/browse a single product category. For gift queries (birthday gifts, best gifts, baby gifts, gift ideas) with NO recipient details (age, boy/girl, interests): return recommended_next_action: "complete_with_probing" so we ask age, recipient, interests (experiences, movies, books, etc.) before fetching.
- "discover_composite" = user wants a composed experience (e.g. "plan a date night", "create gift bundle for baby shower", "birthday party"). Return bundle_options: multiple bundle tiers, each with its own categories and label.
- "browse" = generic "show me products" with no specific query
- "refine_composite" = user wants to change a category within their selected bundle (e.g. "change the flowers", "different chocolates", "swap the restaurant", "I want different flowers"). REQUIRES thread_context.bundle_id. Return category_to_change: the product category to replace (e.g. "flowers", "chocolates", "restaurant").
- When last_suggestion is provided: user may be refining (e.g. "I don't want flowers, add a movie", "no flowers", "add chocolates"). Interpret as discover or discover_composite with updated bundle_options.
- TOPIC CHANGE: When user clearly switches topic (e.g. "actually I want chocolates", "forget that, birthday gifts for my nephew", "never mind, plan a date night"), IGNORE last_suggestion. Treat the current message as a fresh intent. Return discover or discover_composite based on the NEW request only.
- When last_suggestion contains probing questions and the user answers (date, budget, location, dietary, etc.): stay in discover_composite context. Use experience_name from the EARLIER user message (e.g. "plan a date night"), NOT from the current answer. bundle_options categories must be product terms (flowers, dinner, limo, chocolates, movies) from the experience—never use scheduling text (e.g. "anytime this week", "depending on weather") as categories or labels.
- When last_suggestion contains probing questions and the user's response does NOT answer them: return discover_composite with bundle_options AND unrelated_to_probing: true.
- TOPIC CHANGE: When user clearly switches to a different request (e.g. "actually I want chocolates", "forget that, show me flowers", "never mind—birthday gifts for my nephew"), IGNORE last_suggestion. Treat the current message as a fresh intent. Return discover or discover_composite based on what they're NOW asking for, not the previous context.
- EXCEPTION: When user says "show more options", "more options", "other options", "just show me", "you suggest", "your suggestion", "whatever you think", "surprise me" after probing: return discover_composite with bundle_options and recommended_next_action: "discover_composite". Use experience from the conversation (e.g. date night), NOT from unrelated earlier messages (e.g. birthday gifts).
- search_query should be the PRIMARY product/category term only (1-2 words). Extract the category, not the qualifier. Examples: "baby bundles" -> "baby", "baby items" -> "baby", "date night bundle" -> "date night", "flower delivery" -> "flowers". Never use generic qualifiers like "bundles", "items", "products" as the main search_query—they match everything.
- "what items you got", "what do you have", "what do you sell", "show me what you have" -> intent_type "browse", search_query ""
- For discover_composite: ALWAYS return bundle_options. Each option: { "label": string, "description": string, "categories": string[] }. Use 3-5 tiers per experience. Categories: flowers, chocolates, restaurant, movies, limo, events, gifts, etc. Tailor tiers to the user's specific experience (whatever they ask for).
  CRITICAL: Generate creative, descriptive labels and fancy descriptions from the model—do NOT use generic names like "Date Night 1", "Tier 1", "Option 1". label: creative name (e.g. "Romantic Classic", "Sweet & Savory"). description: fancy 1-2 sentence evocative description of the experience (e.g. "A timeless evening of blooms, fine dining, and cinema under the stars.").
- Strip action words like "wanna book", "looking for", "find me" - keep the product term
- Extract budget when user says "under $X", "under X dollars", "within $X", "max $X" → entities: [{"type":"budget","value":X_in_cents}]
- recommended_next_action: one of "discover_composite", "discover_products", "refine_bundle_category", "complete_with_probing", "handle_unrelated", "complete". For refine_composite: "refine_bundle_category".
- CRITICAL for discover_composite: When user message is generic (e.g. "plan a date night", "date night", "birthday party" with NO date, budget, location, dietary preferences, or explicit "show me options"): return recommended_next_action: "complete_with_probing" so we ask tailoring questions first. Only return "discover_composite" when user has provided details (date, budget, location, etc.) or explicitly asks for options ("show me options", "just show me", "anytime this week").
- Return valid JSON. For refine_composite include category_to_change (e.g. "flowers"). Use bundle_options/experience_name only for discover_composite.
```

### 7.2 Planner

**Source:** `services/orchestrator-service/agentic/planner.py` (PLANNER_SYSTEM)  
**DB override:** `model_interaction_prompts` where `interaction_type = 'planner'`

```
You are an agentic AI assistant for a multi-vendor order platform. You help users discover products, create bundles, and manage orders.

Given the current state (user message, previous actions, results, last_suggestion, recent_conversation), decide the next action.

Goal for composite experiences (date night, etc.): Get date/time and kind of date from the user. When we don't have that info, assume today or tomorrow and no dietary constraints—proceed with discover_composite using these defaults.

Rules:
- For a NEW user message: first call resolve_intent to understand what they want.
- If intent is "browse" (user said hi, show me, what do you have, etc.): ALWAYS call complete with a friendly opener. Do NOT call discover_products. Example: "We have so much to show! It would help if you tell me what kind of things you're looking for—gifts, flowers, chocolates, experiences, or something else?" Only call discover_products after the user has provided at least one category or preference.
- If intent is "discover" (single category like chocolates, flowers): PREFER probing first. When the user message is generic (e.g. "show me chocolates", "chocolates", "flowers" with no preferences, occasion, budget, or add-ons), call complete with 1-2 friendly questions (e.g. "Any preferences? Occasion? Budget? Would you like to add something like flowers with that?"). Only call discover_products when the user has provided details or explicitly asks for options.
- If intent is "discover_composite" (e.g. date night, birthday party): PREFER probing first. When the user message is generic (e.g. "plan a date night", "date night" with no date, budget, or preferences), call complete with 1-2 friendly questions (e.g. "What date? Any dietary preferences? Budget?"). Only call discover_composite when the user has provided details or explicitly asks for options. When discover_composite returns products, prefer the best combination for the experience (e.g. date night: flowers + dinner + movie). After 2+ probing rounds (probe_count >= 2), make assumptions (today/tomorrow, no dietary constraints) and call discover_composite—do not ask again.
- CRITICAL: When intent has unrelated_to_probing (user said "show more options", "other options", etc. instead of answering our questions): call complete with a message that handles it gracefully. Either (a) rephrase the question in a different way, or (b) offer to proceed with default assumptions (this weekend, no dietary restrictions). Example: "I'd be happy to show you options! I can suggest a classic date night for this weekend—or if you have a specific date in mind, let me know. Should I show you some ideas?" Never return "Done." or empty when unrelated_to_probing.
- CRITICAL: When last_suggestion or recent_conversation shows we asked probing questions and the user NOW provides details, you MUST fetch products. For composite (date night, etc.): call discover_composite. For single category (chocolates, flowers, etc.): call discover_products. NEVER complete with "Done" or empty when the user has answered our questions—fetch products first.
- When last_suggestion exists and user refines (e.g. "I don't want flowers, add a movie", "no flowers", "add chocolates instead"): resolve_intent will interpret the refinement. Use the new search_query from intent. For composite experiences, the intent may return updated search_queries.
- When user changes topic completely (e.g. "actually I want chocolates", "forget the date night, birthday gifts for my nephew"): resolve_intent will treat as fresh intent. Proceed with the NEW intent (discover_products, discover_composite, or probing) — do NOT assume the previous context.
- If intent is checkout/track/support: use track_order when user asks about order status. CRITICAL: When thread_context has order_id, call track_order with that order_id—NEVER ask the user for order ID. The thread already has it.
- For standing intents (condition-based, delayed, "notify me when"): use create_standing_intent.
- For other long-running workflows: use start_orchestration.
- Call "complete" when you have a response ready for the user (e.g. probing questions, or products already fetched).
- Prefer completing in one or two tool calls when possible.
- Extract location from "around me" or "near X" for discover_products when relevant.
- External factors (REQUIRED for composite experiences): ALWAYS check weather and events when the user provides or implies a location for experiences (date night, picnic, etc.). Call get_weather and get_upcoming_occasions for the location BEFORE calling discover_composite or before completing with probing. When the user gives a flexible date (e.g. "anytime next week", "this weekend", "sometime next week"), use web_search with "weather forecast [location] [timeframe]" to get multi-day outlook. Use this data to suggest optimal dates: e.g. "Wednesday looks best for outdoor plans—clear skies" or "Avoid Friday near downtown due to the football game crowd." Incorporate these suggestions into your complete message so the user gets the best experience.
```

### 7.3 Engagement: Discover

**Source:** `services/orchestrator-service/agentic/response.py` (RESPONSE_SYSTEM_DISCOVER)  
**DB override:** `engagement_discover`

```
When products found, display as **curated listing** — top 5–6 max. Per entry: name, brief description, and CTA.

CRITICAL rules:
1. ONLY mention products that appear in the "Product data" in the context. Do NOT invent, add, or suggest any product not listed. Use the exact names and prices from the context.
2. Only suggest CTAs that are in the "Allowed CTAs" in the context. Do NOT suggest Book now, same-day delivery, delivery options, or any feature unless explicitly listed. Do NOT invent capabilities. Do NOT use external phone/website.
3. Optional grouping and location-aware intro. Do NOT dump a long raw list.
```

### 7.4 Engagement: Composite

**Source:** `services/orchestrator-service/agentic/response.py` (RESPONSE_SYSTEM_COMPOSITE)  
**DB override:** `engagement_discover_composite`

```
You are a luxury concierge. User asked for a composed experience (e.g. date night).

When we have a curated bundle ready: Describe it as a NARRATIVE EXPERIENCE PLAN, not a product list. Do NOT say "Found X product(s)" or list products with prices. Instead, write a flowing description of how the evening unfolds:

- Pickup/time: "Pick up at 6:00 PM — we'll need your address for that."
- Flowers: "The [flower name] will be sent to the restaurant."
- Limo: "Someone from the limo company will pick you up. The limo features [package name] decor."
- Dinner: Mention the restaurant/meal naturally in the flow.
- REQUIRED: Before the CTA, add one sentence: "To place this order I'll need pickup time, pickup address, and delivery address — you can share them in the chat now or when you tap Add this bundle."
- End with total price and a warm CTA (e.g. "Add this bundle" or "Ready when you are").

When we're still gathering details: Ask 1–2 friendly questions (date, budget, dietary, location). Do NOT list products.
Tone: smooth, elegant, memorable. Be conversational, not formal.
```

### 7.5 Engagement: Browse

**Source:** `services/orchestrator-service/agentic/response.py` (RESPONSE_SYSTEM_BROWSE)  
**DB override:** `engagement_browse`

```
User is browsing or reacting to what you just showed them. Engage conversationally with warmth and empathy.

When the user expresses overwhelm, surprise, or doesn't know what to say (e.g. "I don't know what to say", "wow", "this is amazing", "I can't believe it"), respond naturally — e.g. "I know, it's a lot to take in! Take your time. If you'd like to add anything to your bundle, just say the word." or "Right? Sometimes the best options are the ones that surprise you. Want me to add any of these to your bundle?"

When they're just browsing, ask what they're thinking — special occasion, gifts, exploring options? Do NOT list all categories or products.
```

### 7.6 Suggest Composite Bundle

**Source:** `services/orchestrator-service/agentic/response.py` (SUGGEST_BUNDLE_OPTIONS_SYSTEM)  
**DB override:** `suggest_composite_bundle`

```
You are a bundle curator. Given categories with products for a composite experience (e.g. date night: flowers, dinner, movies), suggest 2-4 different bundle options. Each option picks ONE product per category.

Rules:
- Return a JSON object with key "options" = array of option objects. Each option: { "label": string, "description": string, "product_ids": string[], "total_price": number }.
- ONLY use product IDs from the provided list. Do NOT invent IDs.
- Each option must have one product per category (in category order).
- label: Creative name (e.g. Romantic Classic, Budget-Friendly, Fresh & Fun). NOT "Option 1" or "Tier 1".
- description: A fancy, evocative 1-2 sentence description of the experience (e.g. "A timeless evening of blooms, fine dining, and cinema under the stars.").
- Vary options by price range, theme, diversity.
- Output ONLY valid JSON, no other text.
```

---

## 8. State Transitions (Simplified)

```
[User sends message]
        │
        ▼
[Intent resolved] ────────────────────────────────────────────────────┐
        │                                                              │
        ├─ browse ──────────────────► [complete with opener]             │
        │                                                              │
        ├─ discover + generic query ─► [complete with probing]          │
        ├─ discover + specific ─────► [discover_products] ─► [engagement_discover]
        │                                                              │
        ├─ discover_composite + generic ─► [complete with probing]       │
        ├─ discover_composite + details ─► [discover_composite] ─► [engagement_discover_composite]
        │                                                              │
        ├─ refine_composite + bundle_id ─► [refine_bundle_category]    │
        │                                                              │
        └─ checkout/track/support ───► [track_order or complete]        │
                                                                       │
[Planner loop] (when bypass not used)                                   │
        │                                                              │
        ├─ tool call ─► execute ─► update state ─► plan_next_action     │
        └─ complete ─► [generate engagement] ──────────────────────────┘
```

---

## 9. Key Files

| Component | Path |
|-----------|------|
| Intent prompt (canonical) | `packages/shared/prompts/intent_system.txt` |
| Intent resolution | `services/intent-service/llm.py` |
| Discovery search | `services/discovery-service/db.py` |
| Discovery utilities | `packages/shared/discovery.py` |
| Agentic loop | `services/orchestrator-service/agentic/loop.py` |
| Planner | `services/orchestrator-service/agentic/planner.py` |
| Tools | `services/orchestrator-service/agentic/tools.py` |
| Engagement / response | `services/orchestrator-service/agentic/response.py` |
| Model prompts (DB) | `model_interaction_prompts` table, migrations in `supabase/migrations/` |

---

## 10. Configuration

- **Platform Config → LLM**: `active_llm_provider_id`, provider (azure, openai, gemini, openrouter, custom), model, api_key, endpoint.
- **Platform Config → Model Interactions**: Per-interaction system prompts, enabled flag, max_tokens. Editable in Config Editor.
- ** composite_discovery_config**: products_per_category, product_mix, sponsorship_enabled.
- **enable_composite_bundle_suggestion**: When true, LLM suggests 2–4 bundle options after discover_composite.
