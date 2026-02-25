"""LLM-generated engagement response - natural user-facing message instead of templated summary."""

import asyncio
import json
import logging
import queue
import threading
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

RESPONSE_SYSTEM = """You are a friendly shopping assistant. Given the user's message and what was found/done, write a brief, natural 1-3 sentence response to the user.

Be conversational and helpful. Mention key findings (e.g. product categories, count) without listing everything. Invite the user to add items to their bundle or ask for more.
Do NOT use markdown, bullets, or formal structure. Keep it under 100 words.
"""

# When adaptive cards are off, we allow markdown so the client can render formatted text
RESPONSE_SYSTEM_MARKDOWN_NOTE = """FORMATTING: Reply in markdown. You may use **bold**, lists, headings, and line breaks for clarity and emphasis. The message will be rendered as markdown. Keep it concise."""
RESPONSE_SYSTEM_MARKDOWN_REPLACE = "Do NOT use markdown, bullets, or formal structure."
RESPONSE_SYSTEM_MARKDOWN_WITH = "You may use markdown (**bold**, lists, line breaks) for structure and emphasis."

RESPONSE_SYSTEM_COMPOSITE = """You are a luxury Universal Services Orchestrator Concierge (Proactive Concierge, not a form-filler).

Tone & Style: [INJECT ADMIN_CONFIG.GLOBAL_TONE AND LANGUAGE].

**Concierge Narrative Assembly:**
1. STORYTELLING: Write ONE flowing journey (e.g. "Your evening in Dallas begins at 6 PM..."). Do not list products like a receipt or bullet points. One continuous narrative that walks the user through the experience in order.
2. GROUNDEDNESS: Use ONLY the product names and the "features" list from the Product data below. Do NOT invent amenities (e.g. do not mention "champagne" unless it appears in that product's features). If no features are listed for a product, describe only its name and role in the flow.
3. TRANSPARENCY: Calculate and display a single Total Cost of Ownership (TCO) that sums all vendors in the bundle. Show it once at the end (e.g. "Total for your evening: USD 247.00"). No per-product price list in the narrative.

Weave weather/event data naturally when provided (e.g. "With a crisp 65° evening, your indoor table is secured...").
When we're still gathering details: Ask 1–2 friendly questions (date, budget, location). Do NOT list products.
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


# Applied to all engagement responses: model must respect user's stated wants/constraints from their message
RESPONSE_USER_PREFERENCE_RULE = (
    "Respect the user's stated preferences: from their message, infer what they want and what they reject or narrow. "
    "Do not mention, assume, or frame the response around things they rejected or did not ask for; frame only around what they asked for."
)


def _build_context(result: Dict[str, Any]) -> str:
    """Build context string for the LLM from the orchestration result."""
    data = result.get("data") or {}
    intent = data.get("intent") or {}
    products = data.get("products") or {}
    engagement = data.get("engagement") or {}

    parts = []
    planner_msg = (result.get("planner_complete_message") or "").strip()
    if planner_msg and planner_msg.lower() not in ("processed your request.", "done.", "complete."):
        parts.append(f"Planner suggested reply (use or adapt naturally): {planner_msg[:500]}")
    intent_type = intent.get("intent_type", "unknown")
    parts.append(f"Intent: {intent_type}")

    # Use purged proposed_plan from intent (e.g. after "no limo" → Flowers, Dinner only) so reply doesn't echo removed categories
    proposed_plan = intent.get("proposed_plan")
    if isinstance(proposed_plan, list) and proposed_plan:
        parts.append(f"Current plan — use ONLY these categories in your reply: {', '.join(str(p) for p in proposed_plan)}.")
    # Bundle themes from intent (e.g. Romantic Date Night, Casual, Adventure) — pass labels + descriptions so we can present them to the user
    bundle_opts = intent.get("bundle_options") or []
    if isinstance(bundle_opts, list) and bundle_opts and intent_type == "discover_composite":
        theme_entries = []
        for o in bundle_opts[:8]:
            if not isinstance(o, dict) or not o.get("label"):
                continue
            label = str(o.get("label", "")).strip()
            desc = (o.get("description") or "").strip() or "A curated experience for you."
            theme_entries.append(f"• {label}: {desc[:120]}")
        if theme_entries:
            parts.append(
                "Themed experience options (PRESENT these to the user — list each with its description so they can choose):\n"
                + "\n".join(theme_entries)
                + "\nAfter listing, invite them to pick one and share date/area so you can tailor it."
            )

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
        exp_cats = (intent.get("experience_categories") or engagement.get("experience_categories") or [])
        if isinstance(exp_cats, list) and exp_cats:
            exp_str = ", ".join(str(t) for t in exp_cats[:12] if t)
            parts.append(
                "User is browsing (open-ended). Base your response on their actual message above. "
                f"Probe what experience they want; use these themes when relevant: {exp_str}. "
                "Do NOT list categories or suggest fetching products until they pick an experience."
            )
        else:
            parts.append(
                "User is browsing (open-ended). Base your response on their actual message above. "
                "Probe what experience they want — e.g. date night, gift, celebration — but phrase it in your own words, not a script. "
                "Do NOT list categories or suggest fetching products until they indicate an experience."
            )
    elif intent_type == "discover_composite":
        exp_name = products.get("experience_name", "experience")
        categories = products.get("categories") or []
        product_list = products.get("products") if isinstance(products, dict) else []
        cat_names = [c.get("query", "") for c in categories if isinstance(c, dict) and c.get("query")]
        suggested_bundles = engagement.get("suggested_bundle_options") or []
        if suggested_bundles:
            # Concierge Narrative: bundle with product features from UCPProduct schema (groundedness)
            opt = suggested_bundles[0]
            product_names = opt.get("product_names") or []
            product_ids = opt.get("product_ids") or []
            total_price = opt.get("total_price")
            currency = opt.get("currency", "USD")
            total_str = f"{currency} {float(total_price):.2f}" if total_price is not None else ""
            # Build product data with features (from categories) so LLM only uses listed features
            id_to_product: Dict[str, Dict[str, Any]] = {}
            for c in categories:
                if isinstance(c, dict):
                    for p in c.get("products", []):
                        if isinstance(p, dict) and p.get("id"):
                            id_to_product[str(p.get("id"))] = p
            product_entries: List[str] = []
            for pid in product_ids:
                p = id_to_product.get(str(pid))
                if not p:
                    continue
                name = p.get("name", "Item")
                pr = p.get("price")
                curr = p.get("currency", "USD")
                price_str = f"{curr} {pr}" if pr is not None else ""
                feats = p.get("features") or []
                if isinstance(feats, str):
                    feats = [f.strip() for f in feats.split(",") if f.strip()]
                feats_str = ", ".join(str(f) for f in feats[:15]) if feats else "(no features listed)"
                product_entries.append(f"{name} ({price_str}) — features: {feats_str}")
            product_data_str = "; ".join(product_entries) if product_entries else ", ".join(product_names)
            missing_ff = engagement.get("missing_fulfillment_fields") or []
            field_labels_ff = engagement.get("fulfillment_field_labels") or {
                "pickup_time": "pickup time",
                "pickup_address": "pickup address",
                "delivery_address": "delivery address",
            }
            need_ff_str = ", ".join(str(field_labels_ff.get(f, f.replace("_", " "))) for f in missing_ff)
            req_cta_line = (
                f"REQUIRED before CTA: 'To place this order I'll need {need_ff_str} — you can share them in the chat now or when you tap Add this bundle.' "
                if need_ff_str
                else "Fulfillment details are set; invite them to Add this bundle and proceed to checkout. "
            )
            parts.append(
                f"User asked for {exp_name}. Curated bundle ready. "
                f"Product data (use ONLY these names and features; do NOT invent amenities): {product_data_str}. "
                f"Total Cost of Ownership (TCO) for the entire bundle: {total_str}. "
                "Write ONE flowing narrative (e.g. 'Your evening in Dallas begins at 6 PM...'). Do NOT list products with prices in the body. "
                + req_cta_line
                + "End with the single TCO and 'Add this bundle' CTA."
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
                f"Present as a curated bundle. ONLY mention products from Product data below—do NOT invent any. Product data (ONLY these): {'; '.join((all_items or [])[:10])}. Be warm and helpful."
            )
        else:
            # No products yet: either present themed ideas (from bundle_options above) or gather details
            if isinstance(bundle_opts, list) and bundle_opts:
                parts.append(
                    "User asked for themed ideas or suggestions. You MUST present the themed experience options listed above (each with its description). "
                    "Then ask for date and area so you can tailor the chosen experience. Do NOT list individual products yet."
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
        _plist = product_list if isinstance(product_list, list) else []
        count = products.get("count", len(_plist)) if isinstance(products, dict) else len(_plist)
        if product_list:
            top_products = product_list[:6] if isinstance(product_list, list) else []
            discover_product_entries: List[str] = []
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
                    discover_product_entries.append(entry)
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
                f"Product data (ONLY these): {'; '.join(discover_product_entries)}"
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
    allow_markdown: bool = False,
    return_debug: bool = False,
):
    """
    Generate a natural, engaging response using the LLM.
    When allow_markdown is True (e.g. no adaptive cards), the model may use markdown and the client should render it.
    Returns None on failure (caller should fall back to templated summary).
    When return_debug is True, returns (summary, debug_dict) with debug_dict having prompt_sent and response_received.
    """
    if result.get("error"):
        if return_debug:
            return (None, {"prompt_sent": "(skipped: result has error)", "response_received": ""})
        return None

    if llm_config is None:
        from api.admin import get_llm_config  # type: ignore[reportMissingImports]
        llm_config = get_llm_config()
    if not llm_config:
        if return_debug:
            return (None, {"prompt_sent": "(skipped: no LLM config)", "response_received": ""})
        return None

    # Use same client builder as admin test (platform_llm) so engagement works when admin config works
    from packages.shared.platform_llm import get_llm_chat_client  # type: ignore[reportMissingImports]
    provider, client = get_llm_chat_client(llm_config)
    if not client:
        if return_debug:
            return (None, {"prompt_sent": "(skipped: no LLM client)", "response_received": ""})
        return None

    cfg = llm_config
    model = cfg.get("model") or "gpt-4o"
    # Use admin model_temperature for creative engagement when available
    try:
        from db import get_admin_orchestration_settings
        admin = get_admin_orchestration_settings()
        if admin and admin.get("model_temperature") is not None:
            temperature = max(0.0, min(2.0, float(admin["model_temperature"])))
        else:
            temperature = min(0.7, float(cfg.get("temperature", 0.1)) + 0.3)
    except Exception:
        temperature = min(0.7, float(cfg.get("temperature", 0.1)) + 0.3)

    data = result.get("data") or {}
    intent = data.get("intent") or {}
    intent_type = intent.get("intent_type", "unknown")
    default_prompt, default_max_tokens = _get_system_prompt_and_max_tokens(intent_type)

    # Use admin-configured prompt from DB when available and enabled
    try:
        from db import get_supabase, get_admin_orchestration_settings
        from packages.shared.platform_llm import get_model_interaction_prompt
        supabase_client = get_supabase()
        interaction_type = _intent_to_interaction_type(intent_type)
        prompt_cfg = get_model_interaction_prompt(supabase_client, interaction_type) if supabase_client else None
        if prompt_cfg and (prompt_cfg or {}).get("enabled", True):
            db_prompt = (prompt_cfg or {}).get("system_prompt")
            db_max = (prompt_cfg or {}).get("max_tokens")
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

    # Inject interaction-stage instructions (Opening: excited, suggest experiences; Narrowing: engage to refine)
    engagement = data.get("engagement") or {}
    stage = engagement.get("interaction_stage", "narrowing")
    try:
        from db import get_admin_orchestration_settings as _get_admin
        admin = _get_admin()
        opening_instructions = (admin or {}).get("opening_instructions") or ""
        narrowing_instructions = (admin or {}).get("narrowing_instructions") or ""
    except Exception:
        opening_instructions = narrowing_instructions = ""
    default_opening = (
        "This is the opening. Be excited about the possibilities; suggest experiences we can offer (e.g. date night, gifts, celebrations). "
        "Invite them to pick an experience or describe what they're looking for. Warm and inviting."
    )
    default_narrowing = (
        "We are narrowing down the plan. Engage to refine; accommodate any changes they suggest. Keep the tone warm and collaborative."
    )
    if stage == "opening" and (opening_instructions.strip() or default_opening):
        system_prompt = (system_prompt.rstrip() + "\n\nStage (opening): " + (opening_instructions.strip() or default_opening)).strip()
    elif stage == "narrowing" and (narrowing_instructions.strip() or default_narrowing):
        system_prompt = (system_prompt.rstrip() + "\n\nStage (narrowing): " + (narrowing_instructions.strip() or default_narrowing)).strip()

    if allow_markdown:
        if RESPONSE_SYSTEM_MARKDOWN_REPLACE in system_prompt:
            system_prompt = system_prompt.replace(RESPONSE_SYSTEM_MARKDOWN_REPLACE, RESPONSE_SYSTEM_MARKDOWN_WITH)
        system_prompt = (system_prompt.rstrip() + "\n\n" + RESPONSE_SYSTEM_MARKDOWN_NOTE).strip()

    # Apply robust user-preference rule so the model respects stated wants/rejections from the message
    system_prompt = (system_prompt.rstrip() + "\n\n" + RESPONSE_USER_PREFERENCE_RULE).strip()

    context = _build_context(result)
    user_content = f"User said: {user_message[:300]}\n\nWhat we did: {context}\n\nWrite a brief friendly response:"
    prompt_sent = f"[System]\n{system_prompt}\n\n[User]\n{user_content}"

    try:
        if provider in ("azure", "openrouter", "custom", "openai"):
            def _call_openai_engagement():
                return client.chat.completions.create(  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            response = await asyncio.to_thread(_call_openai_engagement)
            text = (response.choices[0].message.content or "").strip()
            if return_debug:
                return (text if text else None, {"prompt_sent": prompt_sent, "response_received": text or ""})
            return text if text else None

        if provider == "gemini":
            gen_model = client.GenerativeModel(model)  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
            def _call_gemini_engagement():
                return gen_model.generate_content(
                    f"{system_prompt}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                )
            resp = await asyncio.to_thread(_call_gemini_engagement)
            if resp and resp.candidates:
                text = (getattr(resp, "text", None) or "").strip()
                if return_debug:
                    return (text if text else None, {"prompt_sent": prompt_sent, "response_received": text or ""})
                return text if text else None
    except Exception as e:
        logger.warning("Engagement response LLM failed: %s", e)
    if return_debug:
        return (None, {"prompt_sent": prompt_sent, "response_received": ""})
    return None


async def stream_engagement_response(
    user_message: str,
    result: Dict[str, Any],
    llm_config: Optional[Dict[str, Any]] = None,
    allow_markdown: bool = False,
) -> AsyncIterator[str]:
    """
    Stream engagement response tokens/chunks. Yields each delta; caller can accumulate for full summary.
    If LLM is unavailable or errors, yields nothing (caller should use planner fallback).
    """
    if result.get("error"):
        return
    if llm_config is None:
        try:
            from api.admin import get_llm_config  # type: ignore[reportMissingImports]
            llm_config = get_llm_config()
        except Exception:
            return
    if not llm_config:
        return
    try:
        from packages.shared.platform_llm import get_llm_chat_client  # type: ignore[reportMissingImports]
        provider, client = get_llm_chat_client(llm_config)
    except Exception:
        return
    if not client:
        return

    cfg = llm_config
    model = cfg.get("model") or "gpt-4o"
    try:
        from db import get_admin_orchestration_settings
        admin = get_admin_orchestration_settings()
        if admin and admin.get("model_temperature") is not None:
            temperature = max(0.0, min(2.0, float(admin["model_temperature"])))
        else:
            temperature = min(0.7, float(cfg.get("temperature", 0.1)) + 0.3)
    except Exception:
        temperature = min(0.7, float(cfg.get("temperature", 0.1)) + 0.3)

    data = result.get("data") or {}
    intent = data.get("intent") or {}
    intent_type = intent.get("intent_type", "unknown")
    default_prompt, default_max_tokens = _get_system_prompt_and_max_tokens(intent_type)
    try:
        from db import get_supabase, get_admin_orchestration_settings
        from packages.shared.platform_llm import get_model_interaction_prompt
        supabase_client = get_supabase()
        interaction_type = _intent_to_interaction_type(intent_type)
        prompt_cfg = get_model_interaction_prompt(supabase_client, interaction_type) if supabase_client else None
        if prompt_cfg and (prompt_cfg or {}).get("enabled", True):
            db_prompt = (prompt_cfg or {}).get("system_prompt")
            db_max = (prompt_cfg or {}).get("max_tokens")
            system_prompt = (db_prompt or "").strip() or default_prompt
            max_tokens = db_max if db_max is not None else default_max_tokens
        else:
            system_prompt = default_prompt
            max_tokens = default_max_tokens
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

    # Inject interaction-stage instructions (same as generate_engagement_response)
    engagement = data.get("engagement") or {}
    stage = engagement.get("interaction_stage", "narrowing")
    try:
        from db import get_admin_orchestration_settings as _get_admin_stream
        admin = _get_admin_stream()
        opening_instructions = (admin or {}).get("opening_instructions") or ""
        narrowing_instructions = (admin or {}).get("narrowing_instructions") or ""
    except Exception:
        opening_instructions = narrowing_instructions = ""
    default_opening_s = "This is the opening. Be excited about the possibilities; suggest experiences we can offer. Invite them to pick or describe. Warm and inviting."
    default_narrowing_s = "We are narrowing down the plan. Engage to refine; accommodate changes. Warm and collaborative."
    if stage == "opening" and (opening_instructions.strip() or default_opening_s):
        system_prompt = (system_prompt.rstrip() + "\n\nStage (opening): " + (opening_instructions.strip() or default_opening_s)).strip()
    elif stage == "narrowing" and (narrowing_instructions.strip() or default_narrowing_s):
        system_prompt = (system_prompt.rstrip() + "\n\nStage (narrowing): " + (narrowing_instructions.strip() or default_narrowing_s)).strip()

    if allow_markdown:
        if RESPONSE_SYSTEM_MARKDOWN_REPLACE in system_prompt:
            system_prompt = system_prompt.replace(RESPONSE_SYSTEM_MARKDOWN_REPLACE, RESPONSE_SYSTEM_MARKDOWN_WITH)
        system_prompt = (system_prompt.rstrip() + "\n\n" + RESPONSE_SYSTEM_MARKDOWN_NOTE).strip()
    system_prompt = (system_prompt.rstrip() + "\n\n" + RESPONSE_USER_PREFERENCE_RULE).strip()

    context = _build_context(result)
    user_content = f"User said: {user_message[:300]}\n\nWhat we did: {context}\n\nWrite a brief friendly response:"
    prompt_sent = f"[System]\n{system_prompt}\n\n[User]\n{user_content}"

    def _log_engagement(prompt: str, response: str) -> None:
        max_len = 2000
        p = prompt[:max_len] + f"...(truncated, {len(prompt)} chars)" if len(prompt) > max_len else prompt
        r = response[:max_len] + f"...(truncated, {len(response)} chars)" if len(response) > max_len else response
        logger.info(
            "prompt_trace engagement: %s",
            json.dumps({"prompt_sent": p, "response_received": r}, default=str),
        )

    try:
        if provider in ("azure", "openrouter", "custom", "openai"):
            thread_safe_q: queue.Queue = queue.Queue()

            def _openai_stream() -> None:
                try:
                    stream = client.chat.completions.create(  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                    for chunk in stream:
                        if chunk.choices and len(chunk.choices) > 0:
                            delta = getattr(chunk.choices[0].delta, "content", None)
                            if delta:
                                thread_safe_q.put(delta)
                except Exception as e:
                    thread_safe_q.put(e)
                finally:
                    thread_safe_q.put(None)

            thread = threading.Thread(target=_openai_stream)
            thread.start()
            loop = asyncio.get_event_loop()
            chunks: List[str] = []
            while True:
                item = await loop.run_in_executor(None, thread_safe_q.get)
                if item is None:
                    break
                if isinstance(item, Exception):
                    logger.warning("Engagement stream LLM failed: %s", item)
                    return
                chunks.append(item)
                yield item
            _log_engagement(prompt_sent, "".join(chunks))
            return

        if provider == "gemini":
            gen_model = client.GenerativeModel(model)  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]

            def _gemini_generate() -> Optional[str]:
                try:
                    resp = gen_model.generate_content(
                        f"{system_prompt}\n\n{user_content}",
                        generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                    )
                    if resp and resp.candidates:
                        return (getattr(resp, "text", None) or "").strip()
                except Exception as e:
                    logger.warning("Gemini engagement failed: %s", e)
                return None

            text = await asyncio.to_thread(_gemini_generate)
            if text:
                _log_engagement(prompt_sent, text)
                yield text
    except Exception as e:
        logger.warning("Engagement stream failed: %s", e)


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


def _apply_tier_rotation(
    options: List[Dict[str, Any]],
    last_shown_bundle_label: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Variety leak patch: rotate so a different tier is first (avoid showing same bundle again)."""
    if not options or not last_shown_bundle_label or len(options) < 2:
        return options
    label_lower = (last_shown_bundle_label or "").strip().lower()
    idx = next((i for i, o in enumerate(options) if (o.get("label") or "").strip().lower() == label_lower), -1)
    if idx <= 0:
        return options
    # Put a different tier first: (idx + 1) % n or (idx + 2) % n so user sees variety
    n = len(options)
    start = (idx + 1) % n
    return list(options[start:]) + list(options[:start])


def _build_partner_balanced_options(
    categories: List[Dict[str, Any]],
    experience_name: str = "experience",
    rotate_tier: bool = False,
    last_shown_bundle_label: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    PartnerBalancer: Build 3 tiers with equal representation (no partner twice per tier).
    Tier 1: The Essential (DB heavy), Tier 2: The Premium (UCP heavy), Tier 3: The Express (MCP heavy).
    Multiply relevance by admin_weight from partner_representation_rules.
    When rotate_tier and last_shown_bundle_label are set, reorder so a different tier is first (variety leak patch).
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
    if rotate_tier and last_shown_bundle_label:
        options = _apply_tier_rotation(options, last_shown_bundle_label)
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
        from api.admin import get_llm_config  # type: ignore[reportMissingImports]
        llm_config = get_llm_config()
    if not llm_config:
        return []

    from .planner import _get_planner_client_for_config  # type: ignore[reportMissingImports]
    result = _get_planner_client_for_config(llm_config)
    provider, client = result[0], result[1]
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
            def _call_openai_suggest():
                return client.chat.completions.create(  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
                    model=model,
                    messages=[
                        {"role": "system", "content": SUGGEST_BUNDLE_SYSTEM},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=300,
                )
            response = await asyncio.to_thread(_call_openai_suggest)
            text = (response.choices[0].message.content or "").strip()
        elif provider == "gemini":
            gen_model = client.GenerativeModel(model)  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
            def _call_gemini_suggest():
                return gen_model.generate_content(
                    f"{SUGGEST_BUNDLE_SYSTEM}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": 300},
                )
            resp = await asyncio.to_thread(_call_gemini_suggest)
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
    rotate_tier: bool = False,
    last_shown_bundle_label: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Suggest 2-4 bundle options via PartnerBalancer (equal representation, 3 tiers: DB/UCP/MCP).
    Falls back to LLM when PartnerBalancer yields no options.
    When rotate_tier and last_shown_bundle_label are set, reorder tiers so user sees a different option first (variety leak patch).
    Returns list of { label, description, product_ids, total_price }.
    """
    if not categories:
        return []

    # PartnerBalancer first: 3 tiers, no duplicate partner per tier, admin_weight applied; optional tier rotation
    balanced = _build_partner_balanced_options(
        categories, experience_name,
        rotate_tier=rotate_tier,
        last_shown_bundle_label=last_shown_bundle_label,
    )
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
        from api.admin import get_llm_config  # type: ignore[reportMissingImports]
        llm_config = get_llm_config()
    if not llm_config:
        return []

    from .planner import _get_planner_client_for_config  # type: ignore[reportMissingImports]
    result = _get_planner_client_for_config(llm_config)
    provider, client = result[0], result[1]
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
        if prompt_cfg and (prompt_cfg or {}).get("enabled", True):
            db_prompt = ((prompt_cfg or {}).get("system_prompt") or "").strip()
            if db_prompt:
                system_prompt = db_prompt
            db_max = (prompt_cfg or {}).get("max_tokens")
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
            def _call_openai_suggest_options():
                return client.chat.completions.create(  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            response = await asyncio.to_thread(_call_openai_suggest_options)
            text = (response.choices[0].message.content or "").strip()
        elif provider == "gemini":
            gen_model = client.GenerativeModel(model)  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
            def _call_gemini_suggest_options():
                return gen_model.generate_content(
                    f"{system_prompt}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                )
            resp = await asyncio.to_thread(_call_gemini_suggest_options)
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
