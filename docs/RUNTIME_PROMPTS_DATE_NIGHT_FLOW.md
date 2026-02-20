# Runtime Prompts: "Plan a date night" → "No limo" → "More options"

This document publishes the **actual prompts sent to the models** at runtime for the three user messages in a typical date-night flow. Prompts can be overridden from the database (`model_interaction_prompts`); when no DB row exists, the code defaults below are used.

---

## 1. Intent resolution (Intent service)

**Used for:** Every user message. Resolves to `intent_type`, `search_queries`, `proposed_plan`, `recommended_next_action`, etc.

**Source:** `model_interaction_prompts` (interaction_type = `intent`) or `packages/shared/prompts/intent_system.txt` or code fallback.

### System prompt (code fallback when no DB/file)

```
You are an intent classifier. Return JSON: intent_type, search_query, search_queries, experience_name, bundle_options, entities, recommended_next_action, proposed_plan, confidence_score.
```

### User prompt (template)

Built in `services/intent-service/llm.py`:

```
User message: {text}
[If last_suggestion:] Last suggestion: {last_suggestion[:300]}
[If recent_conversation:] Recent conversation: {role}: {content}; ... (last 4 turns, 80 chars each)
Return valid JSON only.
```

---

### Example: Message 1 — "Plan a date night"

**User content sent to intent model:**

```
User message: Plan a date night

Return valid JSON only.
```

*(No last_suggestion or recent_conversation on first message.)*

**Typical intent result (heuristics or LLM):** `intent_type: discover_composite`, `search_queries: ["flowers", "dinner", "limo"]`, `experience_name: date night`, `proposed_plan: ["Flowers", "Dinner", "Limo"]`, `recommended_next_action: complete_with_probing`.

---

### Example: Message 2 — "No limo"

**User content sent to intent model:**

```
User message: No limo
Last suggestion: I'd love to help you plan a perfect date night! I'm thinking Flowers and Dinner and Limo. What date are you planning for, and which area — e.g. downtown or a neighborhood?

Return valid JSON only.
```

**Typical intent result:** `intent_type: refine_composite`, `removed_categories: ["limo"]`, `search_queries: ["flowers", "dinner"]`, `proposed_plan: ["Flowers", "Dinner"]`, `recommended_next_action: complete_with_probing`.

---

### Example: Message 3 — "more options"

**User content sent to intent model:**

```
User message: more options
Last suggestion: I'd love to help you plan a perfect date night! I'm thinking Flowers and Dinner. What date are you planning for...
Recent conversation: user: Plan a date night; assistant: I'd love to help...; user: No limo; assistant: I'd love to help... Flowers and Dinner...

Return valid JSON only.
```

**Typical intent result:** `intent_type: discover_composite` (or similar), `request_variety: true` possible; state already has `purged_search_queries: ["flowers", "dinner"]` and `purged_proposed_plan: ["Flowers", "Dinner"]` from the previous turn.

---

## 2. Planner (Orchestrator agentic loop)

**Used for:** Deciding the next action (resolve_intent, discover_composite, complete, get_weather, etc.) after each tool result.

**Source:** `model_interaction_prompts` (interaction_type = `planner`) or code default `PLANNER_SYSTEM` in `services/orchestrator-service/agentic/planner.py`.

### System prompt (code default)

```
You are the Agentic Orchestrator. Decide the next tool.

Rule 1: Read Admin Config. If ucp_prioritized is true in state, call fetch_ucp_manifest first before discover_products or discover_composite.

Rule 2: For outdoor/location-based experiences (date night, picnic, etc.), ALWAYS call get_weather and get_upcoming_occasions for the location BEFORE calling discover_composite. Use this data to pivot the plan if necessary (e.g., rain -> suggest "Indoor Dining" instead of "Picnic"). Update the proposed_plan in your reasoning so the frontend Draft Itinerary reflects the pivot.

Rule 3 (Halt & Preview): Do NOT execute discover_composite if location or time is missing. Instead call complete with ONE short concierge message. Use state.proposed_plan and state.entities to acknowledge what the user already gave (e.g. "Today it is! I'm planning your Flowers and Dinner for Downtown. What neighborhood are we looking at?") — never repeat the full 4-question list. The frontend receives proposed_plan as the Draft Itinerary (checklist) while you probe.

Rule 4 (browse / open-ended): For intent browse or generic queries (e.g. "what products do you have", "what do you have", "show me options"), call complete with ONE short message that probes for the EXPERIENCE they want to explore (e.g. romantic, celebration, gift, date night). Do NOT list all product categories; do NOT call discover_products or discover_composite until the user indicates an experience. For intent discover/discover_composite (when they already named an experience), when user has provided location and time (or date), call discover_composite; when they have not, call complete with the short probe above (Rule 3).

Rule 5: When last_suggestion shows probing questions and user NOW provides details, you MUST fetch products. Never complete with "Done" when user answered our questions.

Additional rules:
- For a NEW user message: first call resolve_intent to understand what they want.
- If intent is checkout/track/support: use track_order when user asks about order status. CRITICAL: When thread_context has order_id, call track_order with that order_id—NEVER ask the user for order ID.
- For standing intents: use create_standing_intent. For other long-running workflows: use start_orchestration.
- When intent has unrelated_to_probing: call complete with a graceful message (rephrase or offer default assumptions).
- When user refines (e.g. "no flowers, add a movie"): resolve_intent interprets it. Use the new search_query.
- Extract location from "around me" or "near X" for discover_products when relevant.
- When user gives flexible date (e.g. "anytime next week"), use web_search for weather outlook and suggest optimal dates.
- Metadata: The intent's proposed_plan is passed to the frontend as the Draft Itinerary; ensure your complete message references it (e.g. "your Flowers and Dinner") so the user sees we're building that plan.
- Refinement leak: When intent is refine_composite with removed_categories, use the intent's already-purged search_queries and proposed_plan for discover_composite; do not re-add removed categories.
- Variety leak: When the user asks for "other options" or "show me something else", the intent sets request_variety; the loop will set rotate_tier so the Partner Balancer shows a different tier first. Proceed with discover_composite (or complete with options) as normal.
```

### User prompt (template)

Built in `services/orchestrator-service/agentic/planner.py`:

```
User message: {user_message}

Current state: {json.dumps(state_summary)[:1800]}
```

`state_summary` includes: `iteration`, `probe_count`, `last_tool_result`, `last_suggestion`, `recent_conversation` (last 4 messages, role: content), `thread_context` (order_id, bundle_id), `ucp_prioritized`, `proposed_plan`, `experience_name`, `entities`.

---

### Example: After "Plan a date night" (first turn, intent just returned)

**User content sent to planner:**

```
User message: Plan a date night

Current state: {"iteration": 0, "probe_count": 0, "last_tool_result": {"data": {"intent_type": "discover_composite", "search_queries": ["flowers", "dinner", "limo"], "experience_name": "date night", "proposed_plan": ["Flowers", "Dinner", "Limo"], "recommended_next_action": "complete_with_probing", ...}}, "last_suggestion": null, "recent_conversation": null, "thread_context": {}, "ucp_prioritized": false, "proposed_plan": ["Flowers", "Dinner", "Limo"], "experience_name": "date night", "entities": []}
```

Planner typically returns **complete** with a short probe (e.g. "I'd love to help you plan a perfect date night! I'm thinking Flowers and Dinner and Limo. What date are you planning for, and which area?").

---

### Example: After "No limo" (intent returned refine_composite)

**User content sent to planner:**

```
User message: No limo

Current state: {"iteration": 0, "probe_count": 0, "last_tool_result": {"data": {"intent_type": "refine_composite", "removed_categories": ["limo"], "search_queries": ["flowers", "dinner"], "proposed_plan": ["Flowers", "Dinner"], ...}}, "last_suggestion": "I'd love to help... Flowers and Dinner and Limo. What date...", "recent_conversation": [...], "proposed_plan": ["Flowers", "Dinner"], ...}
```

Planner typically returns **complete** again with a probe that uses only Flowers and Dinner (no limo).

---

### Example: After "more options" (intent returned; may trigger discover_composite)

**User content sent to planner:**

If location/time were already given earlier, state includes `purged_search_queries` and `purged_proposed_plan`. Planner may return **discover_composite** with `search_queries: ["flowers", "dinner"]` (from purged state). If not enough details, planner returns **complete** with another probe.

---

## 3. Engagement response (Orchestrator – natural language reply)

**Used for:** Generating the final assistant message shown to the user (summary).

**Source:** `model_interaction_prompts` by `interaction_type` (`engagement_discover_composite`, `engagement_browse`, `engagement_discover`, `engagement_default`) or code defaults in `services/orchestrator-service/agentic/response.py`. For discover_composite, the placeholder `[INJECT ADMIN_CONFIG.GLOBAL_TONE AND LANGUAGE]` is replaced by `admin_orchestration_settings.global_tone` (e.g. "warm, elegant, memorable").

### System prompt (code default for discover_composite)

```
You are a luxury Universal Services Orchestrator Concierge (Proactive Concierge, not a form-filler).

Tone & Style: warm, elegant, memorable.

**Concierge Narrative Assembly:**
1. STORYTELLING: Write ONE flowing journey (e.g. "Your evening in Dallas begins at 6 PM..."). Do not list products like a receipt or bullet points. One continuous narrative that walks the user through the experience in order.
2. GROUNDEDNESS: Use ONLY the product names and the "features" list from the Product data below. Do NOT invent amenities (e.g. do not mention "champagne" unless it appears in that product's features). If no features are listed for a product, describe only its name and role in the flow.
3. TRANSPARENCY: Calculate and display a single Total Cost of Ownership (TCO) that sums all vendors in the bundle. Show it once at the end (e.g. "Total for your evening: USD 247.00"). No per-product price list in the narrative.

Weave weather/event data naturally when provided (e.g. "With a crisp 65° evening, your indoor table is secured...").
When we're still gathering details: Ask 1–2 friendly questions (date, budget, location). Do NOT list products.
```

### User prompt (template)

Built in `services/orchestrator-service/agentic/response.py`:

```
User said: {user_message[:300]}

What we did: {context}

Write a brief friendly response:
```

`context` is produced by `_build_context(result)` from the orchestration result (intent, products, engagement data).

---

### Example: Message 1 — "Plan a date night" (no products yet)

**Context (What we did):**

```
Intent: discover_composite Current plan — use ONLY these categories in your reply: Flowers, Dinner, Limo. User asked for experience: date night. Categories they want: products. You are a concierge — guide them through a structured flow to gather details for each category. Do NOT list products.
```

**Full user content to engagement model:**

```
User said: Plan a date night

What we did: Intent: discover_composite Current plan — use ONLY these categories in your reply: Flowers, Dinner, Limo. User asked for experience: date night. Categories they want: products. You are a concierge — guide them through a structured flow to gather details for each category. Do NOT list products.

Write a brief friendly response:
```

---

### Example: Message 2 — "No limo"

**Context:** Same structure but with **purged** proposed_plan (no Limo):

```
Intent: refine_composite Current plan — use ONLY these categories in your reply: Flowers, Dinner. Last thing we showed/said to the user: I'd love to help you plan a perfect date night! I'm thinking Flowers and Dinner and Limo... User asked for experience: date night. Categories they want: ... You are a concierge — guide them through a structured flow...
```

So the engagement model is told to use **only** Flowers and Dinner in the reply.

---

### Example: Message 3 — "more options" (after discovery with bundle)

**Context (when suggested_bundle_options and product data exist):**

```
Intent: discover_composite Current plan — use ONLY these categories in your reply: Flowers, Dinner. Last thing we showed/said to the user: ... User asked for date night. Curated bundle ready. Product data (use ONLY these names and features; do NOT invent amenities): Premium Orchid Arrangement (USD 49) — features: ...; Dinner for Two (USD 89) — features: .... Total Cost of Ownership (TCO) for the entire bundle: USD 138.00. Write ONE flowing narrative... REQUIRED before CTA: 'To place this order I'll need pickup time...' End with the single TCO and 'Add this bundle' CTA.
```

**Full user content to engagement model:**

```
User said: more options

What we did: Intent: discover_composite Current plan — use ONLY these categories in your reply: Flowers, Dinner. ... Product data (use ONLY these names and features...): ... TCO: USD 138.00. Write ONE flowing narrative... End with the single TCO and 'Add this bundle' CTA.

Write a brief friendly response:
```

---

## Summary table

| User message    | Intent model user prompt                    | Planner state highlights                    | Engagement context highlights                                      |
|----------------|---------------------------------------------|---------------------------------------------|--------------------------------------------------------------------|
| Plan a date night | `User message: Plan a date night` + Return JSON | proposed_plan: Flowers, Dinner, Limo         | Intent discover_composite; plan: Flowers, Dinner, Limo; concierge  |
| What products do you have? / What do you have? | User message + Return JSON              | intent_type: browse; skip discover bypass → planner runs          | Intent browse; probe for EXPERIENCE (romantic, celebration, gift, date night); no product list |
| No limo        | User message + Last suggestion (with Limo)   | last_tool_result: refine_composite, purged  | proposed_plan: Flowers, Dinner only                                |
| more options   | User message + Last suggestion + Recent conv| purged_search_queries / purged_proposed_plan| Curated bundle + product data + TCO (no limo categories)          |

---

## Where to override prompts

- **Intent:** DB table `model_interaction_prompts` (interaction_type = `intent`), or file `packages/shared/prompts/intent_system.txt`.
- **Planner:** DB table `model_interaction_prompts` (interaction_type = `planner`). Code default: `services/orchestrator-service/agentic/planner.py` → `PLANNER_SYSTEM`.
- **Engagement:** DB table `model_interaction_prompts` (interaction_type = `engagement_discover_composite`, `engagement_browse`, `engagement_discover`, `engagement_default`). Code defaults: `services/orchestrator-service/agentic/response.py` → `RESPONSE_SYSTEM_COMPOSITE`, `RESPONSE_SYSTEM_BROWSE`, `RESPONSE_SYSTEM_DISCOVER`, `RESPONSE_SYSTEM`.

Global tone for engagement (discover_composite) comes from `admin_orchestration_settings.global_tone` and is injected into the system prompt in place of `[INJECT ADMIN_CONFIG.GLOBAL_TONE AND LANGUAGE]`.
