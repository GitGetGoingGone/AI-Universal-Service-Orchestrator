"""LLM-generated engagement response - natural user-facing message instead of templated summary."""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

RESPONSE_SYSTEM = """You are a friendly shopping assistant. Given the user's message and what was found/done, write a brief, natural 1-3 sentence response to the user.

Be conversational and helpful. Mention key findings (e.g. product categories, count) without listing everything. Invite the user to add items to their bundle or ask for more.
Do NOT use markdown, bullets, or formal structure. Keep it under 100 words.
"""

RESPONSE_SYSTEM_COMPOSITE = """You are a luxury concierge. User asked for [categories]. Two response styles (choose based on fit):

(1) **Detail-gathering flow** — numbered questions for date/time, pickup, trip details, flower type, chocolates, extras.
(2) **Luxury Experience Design** — when categories support a full experience (e.g. limo + flowers + chocolates), present a complete curated plan: phased timing, curated options per category, pro tips, budget guidance, upgrade ideas, personalization hook ('If you tell me occasion, city, budget, style — I'll design a hyper-custom version').

Tone: smooth, elegant, memorable.
**Be flexible**: if user asks for options/prices instead of answering, respond to that. The flow is a guide, not a form.
Do NOT list products. Guide them through structured questions or a curated plan tailored to what they asked for.
"""

RESPONSE_SYSTEM_BROWSE = """User is browsing. Engage conversationally. Ask what they're thinking — special occasion, gifts, exploring options? Do NOT list all categories or products.
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
        if product_list or categories:
            # We have fetched products - present as curated bundle
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
            query = intent.get("search_query", "your search")
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
    if intent_type == "discover":
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
    temperature = min(0.7, float(llm_config.get("temperature", 0.1)) + 0.3)  # Slightly more creative for engagement

    data = result.get("data") or {}
    intent = data.get("intent") or {}
    intent_type = intent.get("intent_type", "unknown")
    default_prompt, default_max_tokens = _get_system_prompt_and_max_tokens(intent_type)

    # Use admin-configured prompt from DB when available and enabled
    try:
        from db import get_supabase
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

SUGGEST_BUNDLE_OPTIONS_SYSTEM = """You are a bundle curator. Given categories with products for a composite experience (e.g. date night: flowers, dinner, movies), suggest 2-4 different bundle options. Each option picks ONE product per category.

Rules:
- Return a JSON object with key "options" = array of option objects. Each option: { "label": string, "description": string, "product_ids": string[], "total_price": number }.
- ONLY use product IDs from the provided list. Do NOT invent IDs.
- Each option must have one product per category (in category order).
- Vary options: e.g. Romantic Classic, Budget-Friendly, Fresh & Fun. Consider price range, theme, diversity.
- Output ONLY valid JSON, no other text."""


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
    Use LLM to suggest 2-4 bundle options. Each option: one product per category.
    Returns list of { label, description, product_ids, total_price }.
    """
    if not categories:
        return []

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

Return JSON: {{ "options": [ {{ "label": "...", "description": "...", "product_ids": ["id1","id2"], "total_price": 99.99 }}, ... ] }}. 2-4 options, one product per category each."""

    valid_ids = {str(p["id"]) for p in product_rows}
    price_map = {str(p["id"]): float(p.get("price") or 0) for p in product_rows}

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
            out.append({
                "label": str(opt.get("label", "Option")),
                "description": str(opt.get("description", "")),
                "product_ids": valid,
                "total_price": float(opt.get("total_price", total)),
            })
        return out
    except Exception as e:
        logger.warning("suggest_composite_bundle_options failed: %s", e)
    return []
