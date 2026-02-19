"""LLM-generated engagement response - natural user-facing message instead of templated summary."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

RESPONSE_SYSTEM = """You are a friendly shopping assistant. Given the user's message and what was found/done, write a brief, natural 1-3 sentence response to the user.

Be conversational and helpful. Mention key findings (e.g. product categories, count) without listing everything. Invite the user to add items to their bundle or ask for more.
Do NOT use markdown, bullets, or formal structure. Keep it under 100 words.
"""

RESPONSE_SYSTEM_COMPOSITE = """You are a luxury Universal Services Orchestrator Concierge.

Tone & Style: [INJECT ADMIN_CONFIG.GLOBAL_TONE AND LANGUAGE].

**The Goal:** Write a flowing, evocative 'Narrative Experience Plan' (e.g., "Your evening begins as the sun sets, with a sleek ride arriving at 6 PM..."). Do not list products like a receipt. Focus on the feeling, the atmosphere, and the flow of the event.

**ANTI-HALLUCINATION STRICT RULES:**
1. You MUST paint a vivid picture, but you may ONLY use the exact product names, features, and capabilities provided in the context data.
2. DO NOT invent amenities. If a Limo is provided, describe a "luxurious, smooth ride," but DO NOT say "enjoy complimentary champagne" unless "champagne" is explicitly listed in the product's features.
3. Weave weather/event data naturally into the narrative (e.g., "Since it will be a crisp 65 degrees, the indoor seating is secured...").

Calculate and display the Total Cost of Ownership (TCO) clearly at the bottom.
Explicitly mention if a partner is 'Verified' via Local/UCP/MCP.

When we're still gathering details: Ask 1–2 friendly questions (date, budget, dietary, location). Do NOT list products.
"""

RESPONSE_SYSTEM_BROWSE = """User is browsing or reacting to what you just showed them. Engage conversationally with warmth and empathy.

When the user expresses overwhelm, surprise, or doesn't know what to say (e.g. "I don't know what to say", "wow", "this is amazing", "I can't believe it"), respond naturally — e.g. "I know, it's a lot to take in! Take your time. If you'd like to add anything to your bundle, just say the word." or "Right? Sometimes the best options are the ones that surprise you. Want me to add any of these to your bundle?"

When they're just browsing, ask what they're thinking — special occasion, gifts, exploring options? Do NOT list all categories or products.
"""

RESPONSE_SYSTEM_DISCOVER = """When products found, display as **curated listing** — top 5–6 max. Per entry: name, brief description, and CTA.

CRITICAL rules:
1. ONLY mention products that appear in the "Product data" in the context. Do NOT invent, add, or suggest any product not listed. Use the exact names and prices from the context.
2. Only suggest CTAs that are in the "Allowed CTAs" in the context. Do NOT suggest Book now, same-day delivery, delivery options, or any feature unless explicitly listed. Do NOT invent capabilities. Do NOT use external phone/website.
3. Optional grouping and location-aware intro. Do NOT dump a long raw list.
"""


def _build_context(result: Dict[str, Any]) -> str:
    """Build context string for the LLM from the orchestration result."""
    data = result.get("data") or {}
    intent = data.get("intent") or {}
    products = data.get("products") or {}
    engagement = data.get("engagement") or {}

    parts = []
    intent_type = intent.get("intent_type", "unknown")
    parts.append(f"Intent: {intent_type}")

    last_suggestion = result.get("last_suggestion")
    if last_suggestion:
        parts.append(f"Last thing we showed/said to the user: {str(last_suggestion)[:400]}")

    # Add engagement context (weather, events, web search, order status) when available
    if engagement:
        eng_parts = []
        if engagement.get("order_status") and "error" not in engagement.get("order_status", {}):
            os = engagement["order_status"]
            status = os.get("status", "unknown")
            payment = os.get("payment_status", "")
            total = os.get("total_amount")
            curr = os.get("currency", "USD")
            items = os.get("items") or []
            item_str = ", ".join(f"{i.get('item_name', '')} x{i.get('quantity', 1)}" for i in items[:5] if isinstance(i, dict))
            eng_parts.append(f"Order status: {status} (payment: {payment}). Total: {curr} {total}. Items: {item_str}")
        if engagement.get("weather"):
            w = engagement["weather"]
            eng_parts.append(f"Weather in {w.get('location', '')}: {w.get('description', '')} ({w.get('temp')}°F)" if w.get("temp") else f"Weather: {w.get('description', '')}")
        if engagement.get("occasions", {}).get("events"):
            evts = engagement["occasions"]["events"][:3]
            eng_parts.append(f"Upcoming events: {', '.join(e.get('name', '') for e in evts if e.get('name'))}")
        if engagement.get("web_search", {}).get("results"):
            res = engagement["web_search"]["results"][:2]
            eng_parts.append(f"Web search: {'; '.join((str(r.get('content', r.get('title', '')) or '')[:80] for r in res if isinstance(r, dict)))}")
        us = engagement.get("upsell_surge") or {}
        if us.get("addon_categories"):
            eng_parts.append(f"Upsell add-ons to suggest: {', '.join(us['addon_categories'])}")
        if us.get("promo_products"):
            for p in us["promo_products"][:2]:
                msg = p.get("promo_message") or f"{p.get('discount_pct', 0)}% off when added before checkout"
                eng_parts.append(f"Promo: {msg}")
        if us.get("apply_surge") and us.get("surge_pct"):
            eng_parts.append(f"Surge pricing: {us['surge_pct']}%")
        if eng_parts:
            parts.append("Engagement context: " + ". ".join(eng_parts))

    if intent_type in ("checkout", "track", "support"):
        if engagement.get("order_status") and "error" not in engagement.get("order_status", {}):
            parts.append("Order status was fetched. Summarize it naturally for the user (status, items, total). Do not ask for order ID.")
        else:
            parts.append(f"User needs help with {intent_type}. Direct them appropriately.")
    elif intent_type == "browse":
        parts.append("User is browsing. Engage conversationally. Ask what they're thinking — special occasion, gifts, exploring? Do NOT list all categories.")
    elif intent_type == "discover_composite":
        exp_name = products.get("experience_name", "experience")
        categories = products.get("categories") or []
        product_list = products.get("products") if isinstance(products, dict) else []
        cat_names = [c.get("query", "") for c in categories if isinstance(c, dict) and c.get("query")]
        suggested_bundles = engagement.get("suggested_bundle_options") or []
        if suggested_bundles:
            # We have a curated bundle — describe as narrative experience plan (pickup, flower delivery, limo, etc.)
            opt = suggested_bundles[0]
            product_names = opt.get("product_names") or []
            total_price = opt.get("total_price")
            currency = opt.get("currency", "USD")
            total_str = f"{currency} {float(total_price):.2f}" if total_price is not None else ""
            parts.append(
                f"User asked for {exp_name}. We have a curated bundle ready. "
                f"Bundle includes (use these exact names): {', '.join(product_names)}. Total: {total_str}. "
                "Describe this as a NARRATIVE EXPERIENCE PLAN: how the evening unfolds (e.g. pickup at 6 PM—need address; flowers sent to restaurant; limo pickup with decor). "
                "REQUIRED: Include this sentence before the CTA: 'To place this order I'll need pickup time, pickup address, and delivery address — you can share them in the chat now or when you tap Add this bundle.' "
                "Do NOT say 'Found X product(s)' or list products with prices. Write a flowing 3–5 sentence description. End with total and 'Add this bundle' CTA."
            )
        elif product_list or categories:
            # Fallback: no bundle yet, present as curated options
            all_items = []
            any_eligible_checkout = False
            for c in categories:
                if isinstance(c, dict):
                    for p in c.get("products", [])[:3]:
                        if isinstance(p, dict):
                            if p.get("is_eligible_checkout"):
                                any_eligible_checkout = True
                            pr = p.get("price")
                            s = p.get("name", "Item")
                            if pr is not None:
                                s += f" ({p.get('currency', 'USD')} {pr})"
                            all_items.append(s)
            if not all_items and product_list:
                for p in (product_list[:6] if isinstance(product_list, list) else []):
                    if isinstance(p, dict):
                        if p.get("is_eligible_checkout"):
                            any_eligible_checkout = True
                        pr = p.get("price")
                        s = p.get("name", "Item")
                        if pr is not None:
                            s += f" ({p.get('currency', 'USD')} {pr})"
                        all_items.append(s)
            allowed_ctas = ["Add to bundle"]
            if any_eligible_checkout:
                allowed_ctas.append("Book now")
            parts.append(
                f"Allowed CTAs (suggest ONLY these): {', '.join(allowed_ctas)}. Do NOT suggest same-day delivery, delivery options, or any feature not listed. "
                f"User asked for {exp_name}. Found products in: {', '.join(cat_names) or 'categories'}. "
                f"Present as a curated bundle. ONLY mention products from Product data below—do NOT invent any. Product data (ONLY these): {'; '.join(all_items[:10])}. Be warm and helpful."
            )
        else:
            parts.append(
                f"User asked for experience: {exp_name}. Categories they want: {', '.join(cat_names) or 'products'}. "
                "You are a concierge — guide them through a structured flow to gather details for each category. Do NOT list products."
            )
    else:
        product_list = products.get("products") if isinstance(products, dict) else []
        if not product_list and isinstance(products, list):
            product_list = products
        count = products.get("count", len(product_list)) if isinstance(products, dict) else len(product_list)
        if product_list:
            top_products = product_list[:6] if isinstance(product_list, list) else []
            product_entries: List[str] = []
            any_eligible_checkout = False
            for p in top_products:
                if isinstance(p, dict):
                    name = p.get("name", "Product")
                    desc = (p.get("description") or "")[:120]
                    price = p.get("price")
                    currency = p.get("currency", "USD")
                    if p.get("is_eligible_checkout"):
                        any_eligible_checkout = True
                    entry = f"{name}"
                    if desc:
                        entry += f" — {desc}"
                    if price is not None:
                        entry += f" ({currency} {price})"
                    product_entries.append(entry)
            allowed_ctas = ["Add to bundle"]
            if any_eligible_checkout:
                allowed_ctas.append("Book now")
            parts.append(f"Allowed CTAs (suggest ONLY these): {', '.join(allowed_ctas)}. Do NOT suggest same-day delivery, delivery options, or any feature not listed.")
            location = None
            entities = intent.get("entities") or []
            for e in entities:
                if isinstance(e, dict) and e.get("type") == "location":
                    location = e.get("value")
                    break
            if location:
                parts.append(f"Location context: {location}.")
            parts.append(
                f"Found {count} products. Format as curated listing (top 5–6). ONLY mention products from Product data below—do NOT invent any. Per entry: use exact name and price from data, brief description, CTA from Allowed CTAs only. "
                f"Product data (ONLY these): {'; '.join(product_entries)}"
            )
        else:
            query = intent.get("search_query")
            sq_list = intent.get("search_queries") or []
            if query is None or str(query).strip() in ("", "None"):
                query = ", ".join(str(q) for q in sq_list[:5] if q) if sq_list else "your search"
            parts.append(f"No products found for '{query}'.")

    return " ".join(parts)


def _intent_to_interaction_type(intent_type: str) -> str:
    """Map intent_type to model_interaction_prompts interaction_type."""
    if intent_type == "discover_composite":
        return "engagement_discover_composite"
    if intent_type == "browse":
        return "engagement_browse"
    if intent_type == "discover":
        return "engagement_discover"
    return "engagement_default"


def _get_system_prompt_and_max_tokens(intent_type: str) -> Tuple[str, int]:
    """Return (system_prompt, max_tokens) for the given intent. Code defaults."""
    if intent_type == "discover_composite":
        return RESPONSE_SYSTEM_COMPOSITE, 800
    if intent_type == "browse":
        return RESPONSE_SYSTEM_BROWSE, 150
    if intent_type in ("discover", "discover_products"):
        return RESPONSE_SYSTEM_DISCOVER, 300
    return RESPONSE_SYSTEM, 150


async def generate_engagement_response(
    user_message: str,
    result: Dict[str, Any],
    llm_config: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Generate a natural, engaging response using the LLM.
    Returns None on failure (caller should fall back to templated summary).
    """
    if result.get("error"):
        return None

    if llm_config is None:
        from api.admin import get_llm_config
        llm_config = get_llm_config()

    from .planner import _get_planner_client_for_config
    provider, client = _get_planner_client_for_config(llm_config)
    if not client:
        return None

    model = llm_config.get("model") or "gpt-4o"
    # Use admin model_temperature for creative engagement when available
    try:
        from db import get_admin_orchestration_settings
        admin = get_admin_orchestration_settings()
        if admin and admin.get("model_temperature") is not None:
            temperature = max(0.0, min(2.0, float(admin["model_temperature"])))
        else:
            temperature = min(0.7, float(llm_config.get("temperature", 0.1)) + 0.3)
    except Exception:
        temperature = min(0.7, float(llm_config.get("temperature", 0.1)) + 0.3)

    data = result.get("data") or {}
    intent = data.get("intent") or {}
    intent_type = intent.get("intent_type", "unknown")
    default_prompt, default_max_tokens = _get_system_prompt_and_max_tokens(intent_type)

    # Use admin-configured prompt from DB when available and enabled
    try:
        from db import get_supabase, get_admin_orchestration_settings
        from packages.shared.platform_llm import get_model_interaction_prompt
        client = get_supabase()
        interaction_type = _intent_to_interaction_type(intent_type)
        prompt_cfg = get_model_interaction_prompt(client, interaction_type) if client else None
        if prompt_cfg and prompt_cfg.get("enabled", True):
            db_prompt = prompt_cfg.get("system_prompt")
            db_max = prompt_cfg.get("max_tokens")
            system_prompt = (db_prompt or "").strip() or default_prompt
            max_tokens = db_max if db_max is not None else default_max_tokens
        else:
            system_prompt = default_prompt
            max_tokens = default_max_tokens
        # Inject admin_config (global_tone) for engagement_discover_composite
        if intent_type == "discover_composite":
            admin = get_admin_orchestration_settings()
            tone = (admin or {}).get("global_tone", "warm, elegant, memorable")
            system_prompt = system_prompt.replace(
                "[INJECT ADMIN_CONFIG.GLOBAL_TONE AND LANGUAGE]",
                tone,
            )
    except Exception:
        system_prompt = default_prompt
        max_tokens = default_max_tokens

    context = _build_context(result)
    user_content = f"User said: {user_message[:300]}\n\nWhat we did: {context}\n\nWrite a brief friendly response:"

    try:
        if provider in ("azure", "openrouter", "custom"):
            def _call():
                return client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            response = await asyncio.to_thread(_call)
            text = (response.choices[0].message.content or "").strip()
            return text if text else None

        if provider == "gemini":
            gen_model = client.GenerativeModel(model)
            def _call():
                return gen_model.generate_content(
                    f"{system_prompt}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                )
            resp = await asyncio.to_thread(_call)
            if resp and resp.candidates:
                text = (getattr(resp, "text", None) or "").strip()
                return text if text else None
    except Exception as e:
        logger.warning("Engagement response LLM failed: %s", e)
    return None


SUGGEST_BUNDLE_SYSTEM = """You are a bundle curator. Given categories with products for a composite experience (e.g. date night: flowers, dinner, movies), pick exactly ONE product per category that best fits the experience.

Rules:
- Return a JSON object with key "product_ids" = array of product IDs (strings), one per category, in category order.
- ONLY use product IDs from the provided list. Do NOT invent IDs.
- If a category has no products, omit it from the array.
- Prefer products that balance quality and value for the occasion.
- Output ONLY valid JSON, no other text."""

SUGGEST_BUNDLE_OPTIONS_SYSTEM = """You are the Bundle Architect. Curate 3 tiers based on the provided categories.

Constraint: Apply the Partner Balancer rules. Never repeat a partner across categories in the same tier.
Provide creative, evocative tier names (e.g. 'The Twilight Classic', 'The Essential', 'The Premium', 'The Express').

Return JSON: { "options": [ { "label": string, "description": string, "product_ids": string[], "total_price": number }, ... ] }.
ONLY use product IDs from the provided list. Each option: one product per category. 2-4 options. Output ONLY valid JSON."""


def _build_partner_balanced_options(
    categories: List[Dict[str, Any]],
    experience_name: str = "experience",
) -> List[Dict[str, Any]]:
    """
    PartnerBalancer: Build 3 tiers with equal representation (no partner twice per tier).
    Tier 1: The Essential (DB heavy), Tier 2: The Premium (UCP heavy), Tier 3: The Express (MCP heavy).
    Multiply relevance by admin_weight from partner_representation_rules.
    """
    try:
        from db import get_partner_representation_rules
        partner_rules = get_partner_representation_rules()
    except Exception:
        partner_rules = {}

    def _weight(pid: str) -> float:
        r = partner_rules.get(str(pid), {})
        return float(r.get("admin_weight", 1.0))

    def _source_score(source: str, tier: int) -> float:
        # tier 1=DB, 2=UCP, 3=MCP
        s = (source or "DB").upper()
        if tier == 1:
            return 1.5 if s == "DB" else (0.7 if s == "UCP" else 0.5)
        if tier == 2:
            return 1.5 if s == "UCP" else (0.7 if s == "DB" else 0.5)
        if tier == 3:
            return 1.5 if s == "MCP" else (0.7 if s == "DB" else 0.5)
        return 1.0

    tier_labels = ["The Essential", "The Premium", "The Express"]
    tier_descriptions = [
        "A curated selection from our trusted local partners.",
        "Premium picks from our verified UCP catalog.",
        "Express options for a quick, seamless experience.",
    ]
    cat_order = [c.get("query", "products") for c in categories if isinstance(c, dict)]
    products_by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for c in categories:
        if not isinstance(c, dict):
            continue
        q = c.get("query", "products")
        prods = []
        for p in (c.get("products") or [])[:10]:
            if isinstance(p, dict) and p.get("id"):
                prods.append({
                    "id": str(p["id"]),
                    "name": p.get("name", "Item"),
                    "price": float(p.get("price", 0)),
                    "currency": p.get("currency", "USD"),
                    "partner_id": str(p.get("partner_id", "") or ""),
                    "source": (p.get("source") or "DB").upper(),
                })
        products_by_cat[q] = prods

    options: List[Dict[str, Any]] = []
    for tier_idx in range(3):
        used_partners: set = set()
        product_ids: List[str] = []
        trace_products: List[Dict[str, Any]] = []
        total_price = 0.0
        currency = "USD"
        for cat in cat_order:
            prods = products_by_cat.get(cat, [])
            best = None
            best_score = -1.0
            best_relevance = 0.0
            best_weight = 1.0
            for p in prods:
                pid = p.get("partner_id", "")
                if pid and pid in used_partners:
                    continue  # Equal representation: no partner twice per tier
                rel = _source_score(p.get("source", "DB"), tier_idx + 1)
                w = _weight(pid or "default")
                score = rel * w
                if score > best_score:
                    best_score = score
                    best = p
                    best_relevance = rel
                    best_weight = w
            if best:
                product_ids.append(str(best["id"]))
                total_price += best.get("price", 0)
                currency = best.get("currency", "USD")
                trace_products.append({
                    "product_id": str(best["id"]),
                    "partner_id": str(best.get("partner_id", "") or ""),
                    "protocol": (best.get("source") or "DB").upper(),
                    "relevance_score": round(best_relevance, 4),
                    "admin_weight": round(best_weight, 4),
                })
                if best.get("partner_id"):
                    used_partners.add(str(best["partner_id"]))
        if product_ids:
            opt = {
                "label": tier_labels[tier_idx] if tier_idx < len(tier_labels) else f"Option {tier_idx + 1}",
                "description": tier_descriptions[tier_idx] if tier_idx < len(tier_descriptions) else "",
                "product_ids": product_ids,
                "total_price": round(total_price, 2),
                "currency": currency,
            }
            if trace_products:
                opt["_trace_products"] = trace_products
            options.append(opt)
    return options


async def suggest_composite_bundle(
    categories: List[Dict[str, Any]],
    user_message: str,
    experience_name: str = "experience",
    budget_max: Optional[int] = None,
    llm_config: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Use LLM to pick one product per category for a suggested bundle.
    Returns list of product IDs (one per category with products), or empty list on failure.
    """
    if not categories:
        return []

    # Build flat list of all products with id, name, price, category
    product_rows: List[Dict[str, Any]] = []
    for c in categories:
        if not isinstance(c, dict):
            continue
        query = c.get("query", "products")
        for p in (c.get("products") or [])[:5]:
            if isinstance(p, dict) and p.get("id"):
                product_rows.append({
                    "id": str(p.get("id", "")),
                    "name": p.get("name", "Unknown"),
                    "price": p.get("price"),
                    "currency": p.get("currency", "USD"),
                    "category": query,
                })

    if not product_rows:
        return []

    if llm_config is None:
        from api.admin import get_llm_config
        llm_config = get_llm_config()

    from .planner import _get_planner_client_for_config
    provider, client = _get_planner_client_for_config(llm_config)
    if not client:
        return []

    model = llm_config.get("model") or "gpt-4o"
    temperature = 0.2

    product_list = "\n".join(
        f"- id={p['id']} name={p['name']} price={p.get('price')} {p.get('currency','USD')} category={p['category']}"
        for p in product_rows
    )
    user_content = f"""Experience: {experience_name}
User said: {user_message[:200]}
{f"Budget max (cents): {budget_max}" if budget_max else ""}

Products (use ONLY these IDs):
{product_list}

Return JSON: {{"product_ids": ["id1", "id2", ...]}} one per category, best fit for the experience."""

    valid_ids = {str(p["id"]) for p in product_rows}

    try:
        if provider in ("azure", "openrouter", "custom"):
            def _call():
                return client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SUGGEST_BUNDLE_SYSTEM},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=300,
                )
            response = await asyncio.to_thread(_call)
            text = (response.choices[0].message.content or "").strip()
        elif provider == "gemini":
            gen_model = client.GenerativeModel(model)
            def _call():
                return gen_model.generate_content(
                    f"{SUGGEST_BUNDLE_SYSTEM}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": 300},
                )
            resp = await asyncio.to_thread(_call)
            text = (getattr(resp, "text", None) or "").strip() if resp and resp.candidates else ""
        else:
            return []

        if not text:
            return []

        # Parse JSON (handle markdown code blocks)
        import json
        data = None
        if "```" in text:
            for block in text.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                try:
                    data = json.loads(block)
                    break
                except json.JSONDecodeError:
                    continue
        if data is None:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return []

        ids = data.get("product_ids") or []
        return [str(i) for i in ids if str(i) in valid_ids][:len(categories)]
    except Exception as e:
        logger.warning("suggest_composite_bundle failed: %s", e)
    return []


async def suggest_composite_bundle_options(
    categories: List[Dict[str, Any]],
    user_message: str,
    experience_name: str = "experience",
    budget_max: Optional[int] = None,
    llm_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Suggest 2-4 bundle options via PartnerBalancer (equal representation, 3 tiers: DB/UCP/MCP).
    Falls back to LLM when PartnerBalancer yields no options.
    Returns list of { label, description, product_ids, total_price }.
    """
    if not categories:
        return []

    # PartnerBalancer first: 3 tiers, no duplicate partner per tier, admin_weight applied
    balanced = _build_partner_balanced_options(categories, experience_name)
    if balanced:
        return balanced

    product_rows: List[Dict[str, Any]] = []
    for c in categories:
        if not isinstance(c, dict):
            continue
        query = c.get("query", "products")
        for p in (c.get("products") or [])[:5]:
            if isinstance(p, dict) and p.get("id"):
                product_rows.append({
                    "id": str(p.get("id", "")),
                    "name": p.get("name", "Unknown"),
                    "price": p.get("price"),
                    "currency": p.get("currency", "USD"),
                    "category": query,
                })

    if not product_rows:
        return []

    if llm_config is None:
        from api.admin import get_llm_config
        llm_config = get_llm_config()

    from .planner import _get_planner_client_for_config
    provider, client = _get_planner_client_for_config(llm_config)
    if not client:
        return []

    model = llm_config.get("model") or "gpt-4o"
    temperature = 0.2

    # Use admin-configured prompt from DB when available
    system_prompt = SUGGEST_BUNDLE_OPTIONS_SYSTEM
    max_tokens = 500
    try:
        from db import get_supabase
        from packages.shared.platform_llm import get_model_interaction_prompt
        supabase = get_supabase()
        prompt_cfg = get_model_interaction_prompt(supabase, "suggest_composite_bundle") if supabase else None
        if prompt_cfg and prompt_cfg.get("enabled", True):
            db_prompt = (prompt_cfg.get("system_prompt") or "").strip()
            if db_prompt:
                system_prompt = db_prompt
            db_max = prompt_cfg.get("max_tokens")
            if db_max is not None:
                max_tokens = db_max
    except Exception:
        pass

    product_list = "\n".join(
        f"- id={p['id']} name={p['name']} price={p.get('price')} {p.get('currency','USD')} category={p['category']}"
        for p in product_rows
    )
    user_content = f"""Experience: {experience_name}
User said: {user_message[:200]}
{f"Budget max (cents): {budget_max}" if budget_max else ""}

Products (use ONLY these IDs):
{product_list}

Return JSON: {{ "options": [ {{ "label": "...", "description": "Fancy 1-2 sentence evocative description", "product_ids": ["id1","id2"], "total_price": 99.99 }}, ... ] }}. 2-4 options, one product per category each. Use creative labels and fancy descriptions."""

    valid_ids = {str(p["id"]) for p in product_rows}
    price_map = {str(p["id"]): float(p.get("price") or 0) for p in product_rows}
    name_map = {str(p["id"]): p.get("name", "Item") for p in product_rows}

    try:
        if provider in ("azure", "openrouter", "custom"):
            def _call():
                return client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            response = await asyncio.to_thread(_call)
            text = (response.choices[0].message.content or "").strip()
        elif provider == "gemini":
            gen_model = client.GenerativeModel(model)
            def _call():
                return gen_model.generate_content(
                    f"{system_prompt}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                )
            resp = await asyncio.to_thread(_call)
            text = (getattr(resp, "text", None) or "").strip() if resp and resp.candidates else ""
        else:
            return []

        if not text:
            return []

        import json
        data = None
        if "```" in text:
            for block in text.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                try:
                    data = json.loads(block)
                    break
                except json.JSONDecodeError:
                    continue
        if data is None:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return []

        options = data.get("options") or []
        cats_with_products = [c for c in categories if isinstance(c, dict) and (c.get("products") or [])]
        num_cats = len(cats_with_products)
        out: List[Dict[str, Any]] = []
        for opt in options[:4]:
            if not isinstance(opt, dict):
                continue
            ids = opt.get("product_ids") or []
            valid = [str(i) for i in ids if str(i) in valid_ids]
            if num_cats > 0 and len(valid) < num_cats:
                continue
            total = sum(price_map.get(i, 0) for i in valid)
            product_names = [name_map.get(i, "Item") for i in valid]
            currency = "USD"
            if product_rows and valid:
                first_p = next((p for p in product_rows if str(p["id"]) == valid[0]), None)
                if first_p:
                    currency = first_p.get("currency", "USD") or "USD"
            out.append({
                "label": str(opt.get("label", "Option")),
                "description": str(opt.get("description", "")),
                "product_ids": valid,
                "product_names": product_names,
                "total_price": float(opt.get("total_price", total)),
                "currency": currency,
            })
        return out
    except Exception as e:
        logger.warning("suggest_composite_bundle_options failed: %s", e)
    return []
