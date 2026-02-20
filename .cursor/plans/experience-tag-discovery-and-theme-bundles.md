# Plan: Experience-tag discovery and theme bundles

## Overview

- **Discovery**: Return `experience_tags` from semantic search; filter and rank/boost by experience tag; expose experience categories.
- **Theme bundles**: Model gets experience categories, suggests 3–4 theme bundles (with `experience_tags` per option); products matched to each bundle by theme; user picks theme then products.
- **Open-ended queries**: Questions like "what products do you have" must return a **probe** that captures **what experience** the user wants to explore (so we can route to the right discovery and use experience categories).

---

## Implementation summary (open-ended → experience probe)

**Implemented:**

1. **Planner** ([services/orchestrator-service/agentic/planner.py](services/orchestrator-service/agentic/planner.py))  
   - **Rule 4** was rewritten. For intent browse or generic queries (e.g. "what products do you have", "what do you have", "show me options"), the planner must call **complete** with one short message that **probes for the experience** the user wants to explore (e.g. romantic, celebration, gift, date night). It must NOT list all product categories and NOT call discover_products or discover_composite until the user indicates an experience. The rule still covers discover/discover_composite (location/time probe) in the same bullet.

2. **Engagement** ([services/orchestrator-service/agentic/response.py](services/orchestrator-service/agentic/response.py))  
   - For **intent_type == "browse"**, the context passed to the engagement LLM was replaced with explicit experience-probe instructions: respond with a short, friendly probe asking what EXPERIENCE they want to explore; mention example themes (date night, celebration, romantic, luxury, gift, baby); do NOT list all categories; do NOT suggest fetching products until they indicate an experience.  
   - **Optional experience_categories**: If `intent.experience_categories` or `engagement.experience_categories` is present (list of strings), that list is injected into the context so the probe can mention real themes (for when GET experience-categories is implemented).

3. **Intent heuristic** ([services/intent-service/llm.py](services/intent-service/llm.py))  
   - **Open-ended product patterns** were added. Phrases such as "what products do you have", "what do you have", "show me what's available", "what can you offer", "what options do you have", "show me your products", "list all options", etc. are matched by regex. For these, the heuristic returns **intent_type: "browse"**, **search_query: "browse"**, and **recommended_next_action: "complete_with_probing"**. This ensures the loop does not call discover_products and the planner/engagement use the browse (experience-probe) path.

---

## Expected behavior

| User says | System does | User sees |
|-----------|-------------|-----------|
| "What products do you have?" | Intent → browse (or discover with generic query). Loop skips discover bypass. Planner runs → **complete** with one message. Engagement generates reply from browse context. | One short, friendly message that **asks what experience** they want (e.g. "What kind of experience are you looking for—something romantic, a celebration, a gift, or a date night? I can suggest themed bundles once I know."). No product list, no category dump. |
| "What do you have?" / "Show me options" / "What's available?" | Same as above (generic query → planner → complete with experience probe). | Same: probe for experience, no discover call. |
| "Something romantic" / "Date night" / "A gift" | Next turn: intent → discover_composite or discover (with experience indicated). Planner may probe for location/time or call discover_composite. | Normal composite or discover flow; products/bundles once details are sufficient. |

When **experience_categories** are later passed in (e.g. from GET experience-categories), the browse probe can mention those exact themes in the reply (e.g. "We have options for romantic, luxury, celebration, night out, gifts, and baby—what sounds like you?").

---

## Open-ended questions → experience probe (addendum)

### Requirement

Open-ended questions (e.g. "what products do you have", "what do you have", "show me options", "what's available") must **not** trigger immediate product listing or generic browse. Instead, the system must respond with a **probe** that asks what **experience** the user wants to explore (e.g. date night, celebration, romantic, luxury, gifts, baby), so that:

1. The user indicates an experience type or theme.
2. We can route to `discover_composite` with theme bundles and experience_tags, or to `discover_products` with an experience-relevant query.
3. Experience categories (from GET experience-categories) can be used to guide the probe wording.

### Implemented behavior

- **[loop.py](services/orchestrator-service/agentic/loop.py)** (lines 535–536): For generic queries (`browse`, `show`, `options`, `what`, `looking`, `stuff`, `things`, `got`, `have`, `""`), `skip_discover_bypass = True`, so we do **not** auto-call `discover_products` and the planner runs.
- **[planner.py](services/orchestrator-service/agentic/planner.py)** Rule 4: For intent browse or generic queries, the planner calls **complete** with one short message that **probes for the experience** they want to explore (e.g. romantic, celebration, gift, date night). It does NOT list all categories and NOT call discover until the user indicates an experience.
- **[response.py](services/orchestrator-service/agentic/response.py)**: For `intent_type == "browse"`, the engagement context instructs the LLM to respond with a short, friendly probe asking what **experience** they want to explore, with example themes; do NOT list all categories; do NOT suggest fetching products until they indicate an experience. Optional `experience_categories` from intent/engagement can be used in the probe wording.
- **[intent-service/llm.py](services/intent-service/llm.py)**: Open-ended product phrases (e.g. "what products do you have", "what do you have", "show me options") are detected by regex and return **intent_type "browse"** and **recommended_next_action "complete_with_probing"** so the flow always uses the experience-probe path.

### Design notes (all implemented)

- **Intent**: Open-ended product phrases return `intent_type: "browse"` and `recommended_next_action: "complete_with_probing"` so the loop never auto-calls discover_products for these.
- **Planner**: Rule 4 instructs the planner to call complete with one message that probes for the experience they want to explore; do not list categories; do not call discover until the user indicates an experience.
- **Engagement**: Browse context instructs the LLM to probe for experience with example themes; optional `experience_categories` can be passed for real theme wording once GET experience-categories exists.
- **Loop**: No change; generic queries already skip discover bypass and the planner produces the experience probe.

### Out of scope (for this addendum)

- Changing the intent API response schema (e.g. adding `probe_for_experience`) is optional; the behavior can be achieved by planner + engagement wording alone.
- Fetching experience-categories before the first probe is optional; the probe can use fixed example themes until the experience-categories API is implemented.

---

## Implementation checklist (open-ended → experience probe)

| # | Area | File(s) | Status |
|---|------|--------|--------|
| 1 | Planner rules | [planner.py](services/orchestrator-service/agentic/planner.py) | **Done**: Rule 4 updated for browse/generic → complete with experience probe; do not list categories; do not call discover until user indicates experience. |
| 2 | Engagement context | [response.py](services/orchestrator-service/agentic/response.py) | **Done**: Browse context asks what experience they want to explore; supports optional `experience_categories` from intent or engagement. |
| 3 | Intent heuristic | [llm.py](services/intent-service/llm.py) | **Done**: Open-ended product patterns (e.g. "what products do you have", "what do you have", "show me options") return intent_type "browse" and recommended_next_action "complete_with_probing". |

---

## Link to main plan

The rest of the implementation (return experience_tags from semantic search, filter/rank by experience tag, experience-categories API, theme bundles with experience_tags, intent returning bundle_options with experience_tags, discover_composite picking products by theme) is described in the main **Experience-tag discovery and theme bundles** plan (file: `experience-tag_discovery_and_theme_bundles_1cf22581.plan.md` in the plan store, or the same content may exist in this repo). This addendum adds the **open-ended → experience probe** behavior so that "what products do you have" leads to a probe that captures the desired experience before any discovery call.
