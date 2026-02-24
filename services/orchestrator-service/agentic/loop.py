"""Agentic decision loop: Observe → Reason → Plan → Execute → Reflect."""

import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import httpx

from clients import get_bundle_details, get_order_status
from .planner import plan_next_action
from .tools import execute_tool

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 15.0


def _get_llm_config() -> Dict[str, Any]:
    from api.admin import get_llm_config  # type: ignore[reportMissingImports]
    return get_llm_config()


async def _web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Call web search API (Tavily or compatible)."""
    from db import get_supabase
    from packages.shared.external_api import get_external_api_config

    client = get_supabase()
    cfg = get_external_api_config(client, "web_search") if client else None
    if not cfg or not cfg.get("api_key"):
        return {"error": "web_search not configured (add web_search external API in Platform Config)"}

    base_url = (cfg.get("base_url") or "https://api.tavily.com").rstrip("/")
    url = f"{base_url}/search" if not base_url.endswith("/search") else base_url
    api_key = cfg.get("api_key", "")

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            # Tavily: POST with api_key in body or Authorization header
            body = {"query": query, "search_depth": "basic", "max_results": min(max_results, 20)}
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = await http.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", data.get("answer", []))
            if isinstance(results, str):
                results = [{"content": results}]
            return {"data": {"results": results[:max_results], "query": query}}
    except Exception as e:
        logger.warning("web_search failed: %s", e)
        return {"error": str(e)}


async def _get_weather(location: str) -> Dict[str, Any]:
    """Call weather API (OpenWeatherMap or compatible)."""
    from db import get_supabase
    from packages.shared.external_api import get_external_api_config

    client = get_supabase()
    cfg = get_external_api_config(client, "weather") if client else None
    if not cfg or not cfg.get("api_key"):
        return {"error": "get_weather not configured (add weather external API in Platform Config)"}

    base_url = (cfg.get("base_url") or "https://api.openweathermap.org").rstrip("/")
    api_key = cfg.get("api_key", "")
    extra = cfg.get("extra_config") or {}
    # OpenWeatherMap: ?q=city&appid=key. Some use lat/lon from extra_config.
    params = {"q": location, "appid": api_key, "units": extra.get("units", "imperial")}

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            resp = await http.get(f"{base_url}/data/2.5/weather", params=params)
            resp.raise_for_status()
            data = resp.json()
            main = data.get("main", {})
            weather = (data.get("weather") or [{}])[0]
            return {
                "data": {
                    "location": location,
                    "temp": main.get("temp"),
                    "feels_like": main.get("feels_like"),
                    "description": weather.get("description", ""),
                    "humidity": main.get("humidity"),
                }
            }
    except Exception as e:
        logger.warning("get_weather failed: %s", e)
        return {"error": str(e)}


async def _get_upcoming_occasions(location: str, limit: int = 5) -> Dict[str, Any]:
    """Call events API (Ticketmaster Discovery or compatible)."""
    from db import get_supabase
    from packages.shared.external_api import get_external_api_config

    client = get_supabase()
    cfg = get_external_api_config(client, "events") if client else None
    if not cfg or not cfg.get("api_key"):
        return {"error": "get_upcoming_occasions not configured (add events external API in Platform Config)"}

    base_url = (cfg.get("base_url") or "https://app.ticketmaster.com/discovery/v2").rstrip("/")
    api_key = cfg.get("api_key", "")
    # Ticketmaster: /events.json?apikey=KEY&city=SanFrancisco
    params = {"apikey": api_key, "city": location.replace(" ", ""), "size": min(limit, 20)}

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            url = f"{base_url}/events.json" if not base_url.endswith(".json") else base_url
            resp = await http.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            events = data.get("_embedded", {}).get("events", [])
            out = []
            for e in events[:limit]:
                name = e.get("name", "")
                url = e.get("url", "")
                dates = e.get("dates", {}).get("start", {})
                out.append({"name": name, "url": url, "date": dates.get("localDate"), "time": dates.get("localTime")})
            return {"data": {"events": out, "location": location}}
    except Exception as e:
        logger.warning("get_upcoming_occasions failed: %s", e)
        return {"error": str(e)}


async def _discover_composite(
    search_queries: List[str],
    experience_name: str,
    discover_products_fn,
    limit: int = 20,
    location: Optional[str] = None,
    partner_id: Optional[str] = None,
    budget_max: Optional[int] = None,
    bundle_options: Optional[List[Dict[str, Any]]] = None,
    fulfillment_hints: Optional[Dict[str, str]] = None,
    theme_experience_tag: Optional[str] = None,
    theme_experience_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Call discover_products per query, compose experience bundle. When bundle_options provided, build multiple bundles with prices. theme_experience_tag or theme_experience_tags filter/boost discovery (multi-tag = AND semantics)."""
    from packages.shared.adaptive_cards.experience_card import generate_experience_card

    categories: List[Dict[str, Any]] = []
    all_products: List[Dict[str, Any]] = []
    item_list_elements: List[Dict[str, Any]] = []
    suggested_bundle_options: List[Dict[str, Any]] = []

    # Use composite_discovery_config.products_per_category when available (default 3 for curated bundle)
    try:
        from api.admin import get_composite_discovery_config  # type: ignore[reportMissingImports]
        cdc = get_composite_discovery_config()
        per_cat = cdc.get("products_per_category")
        if per_cat is not None and isinstance(per_cat, (int, float)):
            per_limit = max(1, min(20, int(per_cat)))
        else:
            per_limit = min(5, max(3, limit // max(1, len(search_queries)))) if search_queries else limit
    except Exception:
        per_limit = min(5, max(3, limit // max(1, len(search_queries)))) if search_queries else limit

    excluded_partners: List[str] = []
    category_products: Dict[str, List[Dict[str, Any]]] = {}  # query -> products

    for q in search_queries:
        if not q or not str(q).strip():
            continue
        exclude_partner_id: Optional[str] = excluded_partners[-1] if excluded_partners else None
        try:
            resp = await discover_products_fn(
                query=str(q).strip(),
                limit=per_limit,
                location=location,
                partner_id=partner_id,
                exclude_partner_id=exclude_partner_id,
                budget_max=budget_max,
                experience_tag=theme_experience_tag,
                experience_tags=theme_experience_tags,
            )
        except Exception as e:
            logger.warning("Discover composite query %s failed: %s", q, e)
            resp = {"data": {"products": [], "count": 0}}
        products = resp.get("data", resp).get("products", [])
        categories.append({"query": q, "products": products})
        category_products[q] = products
        all_products.extend(products)
        # Exclude dominant partner from next category to ensure bundle diversity
        if products:
            from collections import Counter
            partner_counts = Counter(str(p.get("partner_id", "")) for p in products if p.get("partner_id"))
            if partner_counts:
                top_partner = partner_counts.most_common(1)[0][0]
                if top_partner and top_partner not in excluded_partners:
                    excluded_partners.append(top_partner)
        for p in products:
            item_list_elements.append({
                "@type": "Product",
                "name": p.get("name", ""),
                "description": p.get("description", ""),
                "offers": {"@type": "Offer", "price": float(p.get("price", 0)), "priceCurrency": p.get("currency", "USD")},
                "identifier": str(p.get("id", "")),
            })

    # Build suggested_bundle_options from intent's bundle_options (each tier = one product per category, own price)
    def _get_products_for_category(cat: str) -> List[Dict[str, Any]]:
        """Case-insensitive lookup; category_products keys are from search_queries."""
        prods = category_products.get(cat, [])
        if prods:
            return prods
        cat_lower = (cat or "").strip().lower()
        for k, v in category_products.items():
            if (k or "").strip().lower() == cat_lower:
                return v
        return []

    # Narrow-theme keywords: if product name contains these but intent didn't ask for them, deprioritize
    _NARROW_THEME_WORDS = frozenset({"baby", "wedding", "anniversary", "bridal", "newborn", "shower"})

    def _pick_best_product_for_theme(
        products: List[Dict[str, Any]],
        experience_tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Pick the product that best matches the option's experience_tags. Prefer products that don't
        introduce strong themes (e.g. baby, wedding) when the intent didn't ask for them."""
        if not products:
            return None
        tags = [str(t).strip().lower() for t in (experience_tags or []) if t]
        intent_tag_set = set(tags)
        if not tags:
            return products[0]

        def _score(p: Dict[str, Any]) -> Tuple[int, int, int]:
            p_tags = p.get("experience_tags")
            if not isinstance(p_tags, list):
                p_tags = []
            p_set = {str(t).strip().lower() for t in p_tags if t}
            match_count = sum(1 for t in tags if t in p_set)
            extra_tags = len(p_set - intent_tag_set)  # fewer is better
            name_lower = (p.get("name") or "").lower()
            name_theme_penalty = 1 if any(
                w in name_lower for w in _NARROW_THEME_WORDS if w not in intent_tag_set
            ) else 0
            return (match_count, -extra_tags, -name_theme_penalty)

        best = max(products, key=_score)
        return best

    if bundle_options and category_products:
        id_to_product: Dict[str, Dict[str, Any]] = {}
        for prods in category_products.values():
            for p in prods:
                pid = str(p.get("id", ""))
                if pid:
                    id_to_product[pid] = p
        for opt in bundle_options[:10]:
            if not isinstance(opt, dict):
                continue
            opt_cats = [str(c) for c in (opt.get("categories") or []) if c]
            opt_tags = [str(t) for t in (opt.get("experience_tags") or []) if t]
            product_ids: List[str] = []
            total_price = 0.0
            for cat in opt_cats:
                prods = _get_products_for_category(cat)
                p = _pick_best_product_for_theme(prods, opt_tags) if prods else None
                if p:
                    pid = str(p.get("id", ""))
                    if pid:
                        product_ids.append(pid)
                        total_price += float(p.get("price") or 0)
            if product_ids:
                product_names = [id_to_product.get(pid, {}).get("name", "Item") for pid in product_ids]
                currency = "USD"
                if product_ids and id_to_product.get(product_ids[0]):
                    currency = id_to_product[product_ids[0]].get("currency", "USD") or "USD"
                suggested_bundle_options.append({
                    "label": str(opt.get("label", "Option")),
                    "description": str(opt.get("description", "")),
                    "product_ids": product_ids,
                    "product_names": product_names,
                    "total_price": round(total_price, 2),
                    "currency": currency,
                    "categories": opt_cats,
                    "experience_tags": opt_tags,
                })

    # Fallback: when no bundle_options or none matched, build one curated bundle (one product per category)
    if not suggested_bundle_options and category_products:
        product_ids_fb: List[str] = []
        product_names_fb: List[str] = []
        total_price_fb = 0.0
        currency_fb = "USD"
        for q, prods in category_products.items():
            if prods:
                p = prods[0]
                pid = str(p.get("id", ""))
                if pid:
                    product_ids_fb.append(pid)
                    product_names_fb.append(p.get("name", "Item"))
                    total_price_fb += float(p.get("price") or 0)
                    currency_fb = p.get("currency", "USD") or currency_fb
        if product_ids_fb:
            suggested_bundle_options.append({
                "label": (experience_name or "Curated").replace("_", " ").title(),
                "description": "A curated selection for your experience.",
                "product_ids": product_ids_fb,
                "product_names": product_names_fb,
                "total_price": round(total_price_fb, 2),
                "currency": currency_fb,
                "categories": list(category_products.keys()),
            })

    adaptive_card = generate_experience_card(
        experience_name or "experience",
        categories,
        suggested_bundle_options=suggested_bundle_options if suggested_bundle_options else None,
        fulfillment_hints=fulfillment_hints,
    )
    machine_readable = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "numberOfItems": len(all_products),
        "itemListElement": item_list_elements,
    }
    data: Dict[str, Any] = {
        "experience_name": experience_name or "experience",
        "categories": categories,
        "products": all_products,
        "count": len(all_products),
    }
    if suggested_bundle_options:
        data["suggested_bundle_options"] = suggested_bundle_options
    return {
        "data": data,
        "adaptive_card": adaptive_card,
        "machine_readable": machine_readable,
    }


def _generate_refinement_card(
    category: str,
    leg_to_replace: Dict[str, Any],
    alternatives: List[Dict[str, Any]],
    bundle_id: str,
) -> Dict[str, Any]:
    """Build Adaptive Card with 'Replace with this' for each alternative."""
    from packages.shared.adaptive_cards.base import create_card, text_block, container, _filter_empty, strip_html

    leg_id = str(leg_to_replace.get("id", ""))
    body = [
        text_block(f"Choose a different {category.replace('_', ' ')}", size="Medium", weight="Bolder"),
        text_block(f"Replacing: {leg_to_replace.get('name', 'item')}", size="Small", is_subtle=True),
    ]
    for p in alternatives[:5]:
        name = p.get("name", "Unknown")
        price = p.get("price", 0)
        currency = p.get("currency", "USD")
        pid = str(p.get("id", ""))
        desc = strip_html(p.get("description") or "")[:80]
        items = [
            text_block(name, weight="Bolder"),
            text_block(f"{currency} {price:.2f}", size="Small"),
        ]
        if desc:
            items.append(text_block(desc, size="Small"))
        body.append({
            "type": "Container",
            "items": items,
            "actions": [{
                "type": "Action.Submit",
                "title": "Replace with this",
                "data": {
                    "action": "replace_in_bundle",
                    "bundle_id": bundle_id,
                    "leg_id": leg_id,
                    "product_id": pid,
                },
            }],
            "style": "emphasis",
        })
    return create_card(body=body)


async def _refine_bundle_category(
    bundle_id: str,
    category: str,
    discover_products_fn,
) -> Dict[str, Any]:
    """Get bundle, find leg in category, discover alternatives, return card with Replace options."""
    try:
        resp = await get_bundle_details(bundle_id)
    except Exception as e:
        logger.warning("get_bundle_details failed: %s", e)
        return {"error": f"Bundle not found: {e}"}
    data = resp.get("data", resp) if isinstance(resp, dict) else resp
    if not data:
        return {"error": "Bundle not found"}
    items = data.get("items") or []
    cat_lower = (category or "").strip().lower()
    leg_to_replace = None
    for item in items:
        caps = item.get("capabilities") or []
        if isinstance(caps, str):
            caps = [caps]
        if any(cat_lower in str(c).lower() for c in caps):
            leg_to_replace = item
            break
    if not leg_to_replace:
        return {"error": f"No {category} item in bundle to replace"}
    try:
        disc = await discover_products_fn(query=category, limit=10)
    except Exception as e:
        logger.warning("discover_products failed: %s", e)
        return {"error": f"Could not fetch alternatives: {e}"}
    products = (disc.get("data", disc) or {}).get("products", [])
    current_pid = str(leg_to_replace.get("product_id", ""))
    alternatives = [p for p in products if str(p.get("id", "")) != current_pid]
    if not alternatives:
        return {"error": f"No alternatives found for {category}"}
    adaptive_card = _generate_refinement_card(category, leg_to_replace, alternatives, bundle_id)
    return {
        "data": {
            "bundle_id": bundle_id,
            "category": category,
            "leg_to_replace": leg_to_replace,
            "alternatives": alternatives[:5],
        },
        "adaptive_card": adaptive_card,
        "summary": f"Here are some {category} options. Pick one to replace in your bundle.",
    }


async def run_agentic_loop(
    user_message: str,
    *,
    user_id: Optional[str] = None,
    limit: int = 20,
    resolve_intent_fn=None,
    discover_products_fn=None,
    start_orchestration_fn=None,
    create_standing_intent_fn=None,
    use_agentic: bool = True,
    max_iterations: int = 5,
    platform: Optional[str] = None,
    thread_id: Optional[str] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
    bundle_id: Optional[str] = None,
    order_id: Optional[str] = None,
    on_thinking: Optional[Callable[[str, Optional[Dict]], Awaitable[None]]] = None,
    thinking_messages: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Run the agentic decision loop until completion.

    If use_agentic=False or planner fails, falls back to direct intent→discover flow.
    """
    if not use_agentic:
        return await _direct_flow(
            user_message,
            user_id=user_id,
            thread_id=thread_id,
            limit=limit,
            resolve_intent_fn=resolve_intent_fn,
            discover_products_fn=discover_products_fn,
        )

    # Derive last_suggestion and probe_count from conversation history
    last_suggestion = None
    probe_count = 0
    probe_keywords = ("budget", "dietary", "preferences", "location", "what date", "occasion", "add flowers", "add something", "?")
    for m in reversed(messages or []):
        if isinstance(m, dict) and m.get("role") == "assistant":
            content = m.get("content") or ""
            if content:
                last_suggestion = str(content)[:500]
            break
    for m in (messages or []):
        if isinstance(m, dict) and m.get("role") == "assistant":
            content = (m.get("content") or "").lower()
            if any(k in content for k in probe_keywords):
                probe_count += 1

    # Build recent_conversation and thread_context for intent-first
    recent_conversation = None
    if messages:
        recent_conversation = [
            {"role": m.get("role", ""), "content": (m.get("content") or "")[:150]}
            for m in messages[-6:]
            if isinstance(m, dict) and m.get("content")
        ]
    thread_context = {}
    if bundle_id:
        thread_context["bundle_id"] = bundle_id
    if order_id:
        thread_context["order_id"] = order_id

    # Admin config for planner (ucp_prioritized → call fetch_ucp_manifest first)
    admin_settings = None
    try:
        from db import get_admin_orchestration_settings
        admin_settings = get_admin_orchestration_settings()
    except Exception:
        pass

    state = {
        "messages": messages or [],
        "last_suggestion": last_suggestion,
        "probe_count": probe_count,
        "last_tool_result": None,
        "iteration": 0,
        "agent_reasoning": [],
        "bundle_id": bundle_id,
        "order_id": order_id,
        "ucp_prioritized": bool(admin_settings and admin_settings.get("ucp_prioritized")),
    }
    # Restore refinement from previous turn (service-level only: load from DB when thread_id present; no client dependency)
    _refinement: Optional[Dict[str, Any]] = None
    if thread_id:
        try:
            from db import get_thread_refinement_context
            _refinement = get_thread_refinement_context(thread_id)
        except Exception:
            pass
    if _refinement:
        if _refinement.get("proposed_plan"):
            state["purged_proposed_plan"] = _refinement["proposed_plan"]
        if _refinement.get("search_queries"):
            state["purged_search_queries"] = _refinement["search_queries"]

    intent_data = None
    products_data = None
    adaptive_card = None
    machine_readable = None
    engagement_data: Dict[str, Any] = {}

    llm_config = _get_llm_config()
    if thinking_messages is None:
        try:
            from api.admin import get_thinking_messages  # type: ignore[reportMissingImports]
            thinking_messages = get_thinking_messages()
        except Exception:
            thinking_messages = {}

    for iteration in range(max_iterations):
        state["iteration"] = iteration

        # Intent-first: call intent on iteration 0 before planner
        if iteration == 0 and intent_data is None and resolve_intent_fn:
            intent_result = await resolve_intent_fn(
                user_message,
                last_suggestion=last_suggestion,
                recent_conversation=recent_conversation,
                probe_count=probe_count,
                thread_context=thread_context if thread_context else None,
            )
            intent_data = intent_result.get("data", intent_result)
            if not intent_data or not isinstance(intent_data, dict) or not intent_data.get("intent_type"):
                intent_data = {
                    "intent_type": "discover",
                    "search_query": "browse",
                    "entities": [],
                    "confidence_score": 0.5,
                    "recommended_next_action": "complete_with_probing",
                }
            state["last_tool_result"] = intent_result
            state["agent_reasoning"].append("Intent-first: resolved user message.")
            await _emit_thinking(on_thinking, "intent_resolved", intent_data or {}, thinking_messages or {})

            # Rules layer: upsell, surge, promo (after intent)
            try:
                from api.admin import get_upsell_surge_rules  # type: ignore[reportMissingImports]
                from agentic.rules import evaluate_upsell_surge_rules
                rules_cfg = get_upsell_surge_rules()
                bundle_item_count = 0  # TODO: get from bundle when available
                rules_out = evaluate_upsell_surge_rules(
                    intent_data or {},
                    rules_cfg,
                    bundle_item_count=bundle_item_count,
                )
                if rules_out.get("addon_categories") or rules_out.get("promo_products") or rules_out.get("apply_surge"):
                    engagement_data["upsell_surge"] = rules_out
            except Exception as e:
                logger.debug("Rules layer skipped: %s", e)

        # Use recommended_next_action when present (iteration 0 only) to decide next step.
        # Skip bypass when discover_products is recommended but query is generic—engage first.
        rec = (intent_data or {}).get("recommended_next_action") if iteration == 0 else None
        sq = (intent_data or {}).get("search_query") or ""
        generic_queries = ("browse", "show", "options", "what", "looking", "stuff", "things", "got", "have", "")
        skip_discover_bypass = rec == "discover_products" and sq.lower().strip() in generic_queries
        # When Intent says browse or probe, derive a search query from the user message (shared utility); if non-generic, run discovery instead of probing
        if iteration == 0 and (rec == "complete_with_probing" or intent_data.get("intent_type") == "browse"):
            from packages.shared.discovery import fallback_search_query
            derived = (fallback_search_query(user_message) or "").strip()
            if derived and derived.lower() not in generic_queries:
                rec = "discover_products"
                intent_data["intent_type"] = "discover"
                intent_data["search_query"] = derived
                sq = derived
        # For clear discover intents (Intent already gave search_query), run discovery even if Intent said probe
        elif rec == "complete_with_probing" and intent_data.get("intent_type") == "discover" and sq.strip() and sq.lower().strip() not in generic_queries:
            rec = "discover_products"
        if rec and rec in ("discover_composite", "discover_products", "refine_bundle_category") and intent_data and not skip_discover_bypass:
            if rec == "refine_bundle_category" and intent_data.get("intent_type") == "refine_composite":
                bid = (thread_context or {}).get("bundle_id") or state.get("bundle_id")
                cat = intent_data.get("category_to_change", "").strip()
                if bid and cat:
                    plan = {
                        "action": "tool",
                        "tool_name": "refine_bundle_category",
                        "tool_args": {"bundle_id": bid, "category": cat},
                        "reasoning": "Intent recommended refine_bundle_category.",
                    }
                    rec = None
                else:
                    plan = None
            elif rec == "discover_composite" and intent_data.get("intent_type") in ("discover_composite", "refine_composite"):
                # Refinement leak: use purged search_queries/proposed_plan from state if present
                sq = state.get("purged_search_queries") or intent_data.get("search_queries") or ["flowers", "restaurant", "movies"]
                # Run discover_composite: on first turn (probe_count 0) show options without requiring location; after that probe if location/time missing
                if not _has_location_or_time(intent_data, user_message) and state.get("probe_count", 0) >= 1:
                    state["orchestrator_state"] = ORCHESTRATOR_STATE_AWAITING_PROBE
                    plan = None  # Let planner run → complete with probing for location/time
                else:
                    plan = {
                        "action": "tool",
                        "tool_name": "discover_composite",
                        "tool_args": {
                            "bundle_options": intent_data.get("bundle_options") or [],
                            "search_queries": sq,
                            "experience_name": intent_data.get("experience_name") or "experience",
                            "location": _extract_location(intent_data),
                            "budget_max": _extract_budget(intent_data),
                        },
                        "reasoning": "Intent recommended discover_composite (or refine_composite with purged categories).",
                    }
            elif rec == "discover_products" and intent_data.get("intent_type") in ("discover", "browse"):
                sq = (intent_data.get("search_query") or "").strip()
                if not sq:
                    from packages.shared.discovery import fallback_search_query
                    sq = fallback_search_query(user_message)
                plan = {
                    "action": "tool",
                    "tool_name": "discover_products",
                    "tool_args": {
                        "query": sq,
                        "limit": limit,
                        "location": _extract_location(intent_data),
                        "budget_max": _extract_budget(intent_data),
                    },
                    "reasoning": "Intent recommended discover_products.",
                }
            else:
                plan = None
            if plan:
                rec = None  # Consume so we don't skip planner again
        else:
            plan = None

        if plan is None:
            ctx = intent_data or {}
            if rec == "complete_with_probing":
                await _emit_thinking(on_thinking, "before_complete_probing", ctx, thinking_messages or {})
            elif rec == "handle_unrelated":
                await _emit_thinking(on_thinking, "before_handle_unrelated", ctx, thinking_messages or {})
            plan = await plan_next_action(
                user_message, state, max_iterations=max_iterations, llm_config=llm_config
            )

        if plan.get("action") == "complete":
            msg = (plan.get("message") or "").strip()
            msg_lower = msg.lower()
            is_probing_msg = "?" in msg or any(k in msg_lower for k in probe_keywords)
            # When intent has unrelated_to_probing, use graceful message (rephrase or offer assumptions)
            if intent_data and intent_data.get("unrelated_to_probing"):
                if not msg or msg == "Done.":
                    msg = "I'd be happy to show you options! I can suggest a classic date night for this weekend—or if you have a specific date in mind, let me know. Should I show you some ideas?"
                state["agent_reasoning"].append(plan.get("reasoning", ""))
                state["planner_complete_message"] = msg
                break
            # Override: if planner said "Done."/empty with no products, and last_suggestion looks like probing,
            # user likely answered our questions—fetch instead of completing
            if (not msg or msg == "Done.") and not products_data and not intent_data:
                ls = (state.get("last_suggestion") or "").lower()
                if ls and any(k in ls for k in probe_keywords):
                    logger.info("Planner completed with no products but last_suggestion suggests probing—calling resolve_intent")
                    plan = {"action": "tool", "tool_name": "resolve_intent", "tool_args": {"text": user_message}, "reasoning": "User answered probing questions, fetching products."}
                    if state.get("last_suggestion"):
                        plan["tool_args"]["last_suggestion"] = state["last_suggestion"]
                    # Fall through to tool execution (don't break)
                else:
                    state["agent_reasoning"].append(plan.get("reasoning", ""))
                    state["planner_complete_message"] = msg or "Processed your request."
                    break
            # Override: after 2+ probes, if planner wants to ask again but we have no products, proceed with assumptions
            elif is_probing_msg and not products_data and state.get("probe_count", 0) >= 2:
                logger.info("Probe count >= 2, proceeding with discover_composite using assumptions")
                if not intent_data:
                    plan = {"action": "tool", "tool_name": "resolve_intent", "tool_args": {"text": user_message}, "reasoning": "Proceeding after 2+ probes with assumptions."}
                    if state.get("last_suggestion"):
                        plan["tool_args"]["last_suggestion"] = state["last_suggestion"]
                else:
                    # We have intent; if discover_composite, call it. Else try discover_products.
                    if intent_data.get("intent_type") == "discover_composite":
                        plan = {
                            "action": "tool",
                            "tool_name": "discover_composite",
                            "tool_args": {
                                "bundle_options": intent_data.get("bundle_options") or [],
                                "search_queries": intent_data.get("search_queries") or ["flowers", "restaurant", "movies"],
                                "experience_name": intent_data.get("experience_name") or "date night",
                            },
                            "reasoning": "Proceeding after 2+ probes with assumptions.",
                        }
                    else:
                        plan = {"action": "tool", "tool_name": "resolve_intent", "tool_args": {"text": user_message}, "reasoning": "Proceeding after 2+ probes."}
                        if state.get("last_suggestion"):
                            plan["tool_args"]["last_suggestion"] = state["last_suggestion"]
            else:
                state["agent_reasoning"].append(plan.get("reasoning", ""))
                state["planner_complete_message"] = msg or "Processed your request."
                break

        if plan.get("action") == "tool":
            tool_name = plan["tool_name"]
            tool_args = plan.get("tool_args", {})
            state["agent_reasoning"].append(plan.get("reasoning", ""))

            # Inject limit, location, budget from intent entities for discover_products
            if tool_name == "discover_products":
                tool_args = dict(tool_args)
                tool_args.setdefault("limit", limit)
                # Never call discover with empty query: derive from user message if intent left it blank
                if not (tool_args.get("query") or "").strip():
                    from packages.shared.discovery import fallback_search_query
                    tool_args["query"] = fallback_search_query(user_message)
                if intent_data:
                    loc = _extract_location(intent_data)
                    if loc:
                        tool_args.setdefault("location", loc)
                    budget_cents = _extract_budget(intent_data)
                    if budget_cents is not None:
                        tool_args.setdefault("budget_max", budget_cents)

            # Inject context for resolve_intent (intent-first or planner-requested)
            if tool_name == "resolve_intent":
                tool_args = dict(tool_args)
                if state.get("last_suggestion"):
                    tool_args.setdefault("last_suggestion", state["last_suggestion"])
                if recent_conversation:
                    tool_args.setdefault("recent_conversation", recent_conversation)
                if probe_count is not None:
                    tool_args.setdefault("probe_count", probe_count)
                if thread_context:
                    tool_args.setdefault("thread_context", thread_context)

            if tool_name == "create_standing_intent":
                tool_args = dict(tool_args)
                tool_args.setdefault("platform", platform)
                tool_args.setdefault("thread_id", thread_id)

            if tool_name == "track_order":
                tool_args = dict(tool_args)
                if not tool_args.get("order_id") and state.get("order_id"):
                    tool_args["order_id"] = state["order_id"]

            # Emit thinking before tool execution
            ctx = dict(intent_data or {})
            ctx["location"] = ctx.get("location") or _extract_location(intent_data) or tool_args.get("location")
            ctx["query"] = tool_args.get("query") or intent_data.get("search_query")
            ctx["experience_name"] = tool_args.get("experience_name") or (intent_data or {}).get("experience_name")
            if tool_name == "get_weather":
                await _emit_thinking(on_thinking, "before_weather", {**ctx, "location": ctx.get("location") or tool_args.get("location", "your area")}, thinking_messages or {})
            elif tool_name == "get_upcoming_occasions":
                await _emit_thinking(on_thinking, "before_occasions", {**ctx, "location": ctx.get("location") or tool_args.get("location", "your area")}, thinking_messages or {})
            elif tool_name == "discover_products":
                await _emit_thinking(on_thinking, "before_discover_products", {**ctx, "query": ctx.get("query") or "options"}, thinking_messages or {})
            elif tool_name == "discover_composite":
                await _emit_thinking(on_thinking, "before_discover_composite", ctx, thinking_messages or {})
            elif tool_name == "fetch_ucp_manifest":
                await _emit_thinking(on_thinking, "before_fetch_ucp_manifest", {"ucp_prioritized": True}, thinking_messages or {})

            if tool_name == "discover_composite" and intent_data and intent_data.get("intent_type") in ("discover_composite", "refine_composite"):
                tool_args = dict(tool_args)
                if not tool_args.get("bundle_options") and intent_data.get("bundle_options"):
                    tool_args["bundle_options"] = intent_data.get("bundle_options")
                # Always prefer purged list when user previously removed categories (e.g. "no limo")
                purged_sq = state.get("purged_search_queries")
                purged_set = {str(c).strip().lower() for c in (purged_sq or []) if c}
                if purged_sq:
                    tool_args["search_queries"] = purged_sq
                    # Filter bundle_options to only tiers whose categories are in purged set (no limo etc.)
                    if purged_set and tool_args.get("bundle_options"):
                        filtered = []
                        for opt in tool_args["bundle_options"]:
                            if not isinstance(opt, dict):
                                continue
                            cats = opt.get("categories") or []
                            if all(str(c).strip().lower() in purged_set for c in cats if c):
                                filtered.append(opt)
                        if filtered:
                            tool_args["bundle_options"] = filtered
                elif not tool_args.get("search_queries"):
                    tool_args["search_queries"] = intent_data.get("search_queries") or []
                if not tool_args.get("experience_name"):
                    tool_args["experience_name"] = intent_data.get("experience_name") or "experience"
                if not tool_args.get("location") and intent_data:
                    tool_args["location"] = _extract_location(intent_data)
                if not tool_args.get("budget_max") and intent_data:
                    tool_args["budget_max"] = _extract_budget(intent_data)

                # External factors: MUST call get_weather and get_upcoming_occasions BEFORE discovery when location known
                loc = tool_args.get("location")
                if loc and str(loc).strip():
                    if not engagement_data.get("weather"):
                        await _emit_thinking(on_thinking, "before_weather", {"location": loc}, thinking_messages or {})
                        weather_result = await _get_weather(loc)
                        engagement_data["weather"] = weather_result.get("data", weather_result)
                    if not (engagement_data.get("occasions") or {}).get("events"):
                        await _emit_thinking(on_thinking, "before_occasions", {"location": loc}, thinking_messages or {})
                        occasions_result = await _get_upcoming_occasions(loc)
                        engagement_data["occasions"] = occasions_result.get("data", occasions_result)

                    # Contextual pivot: rain → swap outdoor for indoor
                    weather_desc = (engagement_data.get("weather") or {}).get("description", "")
                    if weather_desc and "rain" in weather_desc.lower():
                        exp_name = tool_args.get("experience_name", "")
                        sq = tool_args.get("search_queries") or []
                        if _is_outdoor_experience(exp_name, sq):
                            new_sq, new_opts = _pivot_outdoor_to_indoor(sq, tool_args.get("bundle_options"))
                            tool_args["search_queries"] = new_sq
                            tool_args["bundle_options"] = new_opts
                            engagement_data["weather_warning"] = (
                                f"Weather in {loc}: {weather_desc}. We've adjusted your plan for indoor options."
                            )

            async def _discover_composite_fn(search_queries, experience_name, location=None, budget_max=None, bundle_options=None, theme_experience_tag=None, theme_experience_tags=None):
                fulfillment_hints = _extract_fulfillment_hints(intent_data, user_message)
                intent = intent_data or {}
                return await _discover_composite(
                    search_queries=search_queries,
                    experience_name=experience_name,
                    discover_products_fn=discover_products_fn,
                    limit=limit,
                    location=location,
                    budget_max=budget_max,
                    bundle_options=bundle_options,
                    fulfillment_hints=fulfillment_hints,
                    theme_experience_tag=theme_experience_tag or intent.get("theme_experience_tag"),
                    theme_experience_tags=theme_experience_tags or intent.get("theme_experience_tags"),
                )

            async def _refine_bundle_category_fn(bundle_id: str, category: str):
                return await _refine_bundle_category(
                    bundle_id=bundle_id,
                    category=category,
                    discover_products_fn=discover_products_fn,
                )

            result = await execute_tool(
                tool_name,
                tool_args,
                resolve_intent_fn=resolve_intent_fn,
                discover_products_fn=discover_products_fn,
                discover_composite_fn=_discover_composite_fn,
                refine_bundle_category_fn=_refine_bundle_category_fn,
                start_orchestration_fn=start_orchestration_fn,
                create_standing_intent_fn=create_standing_intent_fn,
                web_search_fn=_web_search,
                get_weather_fn=_get_weather,
                get_upcoming_occasions_fn=_get_upcoming_occasions,
                track_order_fn=get_order_status,
            )

            state["last_tool_result"] = result

            if "error" in result:
                state["agent_reasoning"].append(f"Tool error: {result['error']}")
                state["last_error"] = result["error"]
                break

            if tool_name == "resolve_intent":
                intent_data = result.get("data", result)
                # Refinement leak patch: persist purged search_queries and proposed_plan so subsequent turns use them
                if intent_data and intent_data.get("intent_type") == "refine_composite" and intent_data.get("removed_categories"):
                    state["purged_search_queries"] = intent_data.get("search_queries") or []
                    state["purged_proposed_plan"] = intent_data.get("proposed_plan") or []
                elif intent_data and intent_data.get("intent_type") == "refine_composite" and not intent_data.get("removed_categories"):
                    # User added categories back (e.g. "add limo back"); clear purged state
                    state.pop("purged_search_queries", None)
                    state.pop("purged_proposed_plan", None)
                # Do NOT clear purged state when intent is discover_composite (e.g. "show me options")
                # so "no limo" stays in effect until user starts a new plan or adds categories back
                # Variety leak patch: user asked for "other options" / "something else" -> rotate tier next
                if intent_data and intent_data.get("request_variety"):
                    state["rotate_tier"] = True
                # Don't auto-fetch for discover_composite; let planner decide (probe first or fetch)
            elif tool_name == "fetch_ucp_manifest":
                engagement_data["ucp_manifests_fetched"] = True
            elif tool_name == "web_search":
                engagement_data["web_search"] = result.get("data", result)
            elif tool_name == "get_weather":
                engagement_data["weather"] = result.get("data", result)
                wd = result.get("data", result) or {}
                await _emit_thinking(on_thinking, "after_weather", {"weather_desc": wd.get("description", ""), "location": wd.get("location", "")}, thinking_messages or {})
            elif tool_name == "get_upcoming_occasions":
                engagement_data["occasions"] = result.get("data", result)
            elif tool_name == "refine_bundle_category":
                products_data = result.get("data", result)
                adaptive_card = result.get("adaptive_card")
                if products_data:
                    engagement_data["refine_category"] = products_data.get("category")
            elif tool_name == "discover_composite":
                products_data = result.get("data", result)
                adaptive_card = result.get("adaptive_card")
                machine_readable = result.get("machine_readable")
                pc = (products_data or {}).get("products") or []
                await _emit_thinking(on_thinking, "after_discover", {"product_count": len(pc) if isinstance(pc, list) else 0}, thinking_messages or {})
                # OrchestrationTrace: product discovery (composite)
                try:
                    from db import log_orchestration_trace
                    products_meta = [
                        {
                            "product_id": str(p.get("id", "")),
                            "partner_id": str(p.get("partner_id", "") or ""),
                            "protocol": (p.get("source") or "DB").upper(),
                            "relevance_score": 1.0,
                            "admin_weight": 1.0,
                        }
                        for p in pc if isinstance(p, dict) and p.get("id")
                    ]
                    if products_meta:
                        log_orchestration_trace(
                            "product_discovery",
                            thread_id=thread_id,
                            user_id=user_id,
                            experience_name=(products_data or {}).get("experience_name"),
                            metadata={"products": products_meta},
                        )
                except Exception as e:
                    logger.debug("OrchestrationTrace product_discovery (composite) failed: %s", e)
                # Use intent's bundle options when we have 1+; call LLM only when 0 to generate 2-4
                intent_bundles = (products_data or {}).get("suggested_bundle_options") or []
                if len(intent_bundles) >= 1:
                    engagement_data["suggested_bundle_options"] = intent_bundles
                    state["last_shown_bundle_label"] = intent_bundles[0].get("label") if intent_bundles else None
                    # OrchestrationTrace: bundle created (from intent/discover_composite inline)
                    try:
                        from db import log_orchestration_trace
                        trace_options = []
                        for b in intent_bundles:
                            pids = b.get("product_ids") or []
                            trace_options.append({
                                "label": b.get("label"),
                                "products": [{"product_id": pid, "protocol": "DB", "relevance_score": 1.0, "admin_weight": 1.0} for pid in pids],
                            })
                        if trace_options:
                            log_orchestration_trace(
                                "bundle_created",
                                thread_id=thread_id,
                                user_id=user_id,
                                experience_name=(products_data or {}).get("experience_name"),
                                metadata={"options": trace_options},
                            )
                    except Exception as e:
                        logger.debug("OrchestrationTrace bundle_created (intent) failed: %s", e)
                elif products_data and (products_data.get("categories") or products_data.get("products")):
                    await _emit_thinking(on_thinking, "before_bundle", intent_data or {}, thinking_messages or {})
                    try:
                        from api.admin import _get_platform_config  # type: ignore[reportMissingImports]
                        cfg = _get_platform_config() or {}
                        if cfg.get("enable_composite_bundle_suggestion", True) is False:
                            pass  # Skip bundle suggestion when disabled
                        else:
                            from agentic.response import suggest_composite_bundle_options
                            categories = products_data.get("categories") or []
                            budget = _extract_budget(intent_data) if intent_data else None
                            # Variety leak: pass rotate_tier and last_shown_bundle_label for tier rotation
                            options = await suggest_composite_bundle_options(
                                categories=categories,
                                user_message=user_message,
                                experience_name=products_data.get("experience_name", "experience"),
                                budget_max=budget,
                                rotate_tier=state.get("rotate_tier", False),
                                last_shown_bundle_label=state.get("last_shown_bundle_label"),
                            )
                            if options:
                                engagement_data["suggested_bundle_options"] = options
                                state["last_shown_bundle_label"] = options[0].get("label") if options else None
                                state.pop("rotate_tier", None)
                                # OrchestrationTrace: bundle created (from PartnerBalancer/LLM)
                                try:
                                    from db import log_orchestration_trace
                                    trace_options = []
                                    for opt in options:
                                        tps = opt.pop("_trace_products", None)
                                        if tps:
                                            trace_options.append({"label": opt.get("label"), "products": tps})
                                    if trace_options:
                                        log_orchestration_trace(
                                            "bundle_created",
                                            thread_id=thread_id,
                                            user_id=user_id,
                                            experience_name=products_data.get("experience_name"),
                                            metadata={"options": trace_options},
                                        )
                                except Exception as e:
                                    logger.debug("OrchestrationTrace bundle_created failed: %s", e)
                                from packages.shared.adaptive_cards.experience_card import generate_experience_card
                                fulfillment_hints = _extract_fulfillment_hints(intent_data, user_message)
                                adaptive_card = generate_experience_card(
                                    products_data.get("experience_name", "experience"),
                                    categories,
                                    suggested_bundle_options=options,
                                    fulfillment_hints=fulfillment_hints,
                                )
                            else:
                                from agentic.response import suggest_composite_bundle
                                suggested = await suggest_composite_bundle(
                                    categories=categories,
                                    user_message=user_message,
                                    experience_name=products_data.get("experience_name", "experience"),
                                    budget_max=budget,
                                )
                                if suggested:
                                    engagement_data["suggested_bundle_product_ids"] = suggested
                                    # OrchestrationTrace: bundle created (from suggest_composite_bundle LLM)
                                    try:
                                        from db import log_orchestration_trace
                                        trace_options = [{
                                            "label": "Curated",
                                            "products": [{"product_id": pid, "protocol": "DB", "relevance_score": 1.0, "admin_weight": 1.0} for pid in suggested],
                                        }]
                                        log_orchestration_trace(
                                            "bundle_created",
                                            thread_id=thread_id,
                                            user_id=user_id,
                                            experience_name=products_data.get("experience_name"),
                                            metadata={"options": trace_options},
                                        )
                                    except Exception as e:
                                        logger.debug("OrchestrationTrace bundle_created (LLM) failed: %s", e)
                                    from packages.shared.adaptive_cards.experience_card import generate_experience_card
                                    fulfillment_hints = _extract_fulfillment_hints(intent_data, user_message)
                                    adaptive_card = generate_experience_card(
                                        products_data.get("experience_name", "experience"),
                                        categories,
                                        suggested_bundle_product_ids=suggested,
                                        fulfillment_hints=fulfillment_hints,
                                    )
                    except Exception as e:
                        logger.warning("suggest_composite_bundle_options failed: %s", e)
            elif tool_name == "discover_products":
                products_data = result.get("data", result)
                adaptive_card = result.get("adaptive_card")
                machine_readable = result.get("machine_readable")
                pd = products_data or {}
                pc = pd.get("products") or []
                await _emit_thinking(on_thinking, "after_discover", {"product_count": len(pc) if isinstance(pc, list) else 0}, thinking_messages or {})
                # OrchestrationTrace: product discovery
                try:
                    from db import log_orchestration_trace
                    products_meta = [
                        {
                            "product_id": str(p.get("id", "")),
                            "partner_id": str(p.get("partner_id", "") or ""),
                            "protocol": (p.get("source") or "DB").upper(),
                            "relevance_score": 1.0,
                            "admin_weight": 1.0,
                        }
                        for p in pc if isinstance(p, dict) and p.get("id")
                    ]
                    if products_meta:
                        log_orchestration_trace(
                            "product_discovery",
                            thread_id=thread_id,
                            user_id=user_id,
                            query=tool_args.get("query"),
                            metadata={"products": products_meta},
                        )
                except Exception as e:
                    logger.debug("OrchestrationTrace product_discovery failed: %s", e)
            elif tool_name == "create_standing_intent":
                intent_data = intent_data or {}
                intent_data["standing_intent"] = result
            elif tool_name == "track_order":
                engagement_data["order_status"] = result
            elif tool_name == "complete":
                summary = (result.get("summary") or "").strip()
                if summary:
                    state["planner_complete_message"] = summary
                break

    await _emit_thinking(on_thinking, "before_response", intent_data or {}, thinking_messages or {})

    # Build final response
    out = _build_response(
        intent_data=intent_data,
        products_data=products_data,
        adaptive_card=adaptive_card,
        machine_readable=machine_readable,
        agent_reasoning=state.get("agent_reasoning", []),
        user_message=user_message,
        error=state.get("last_error"),
        engagement_data=engagement_data,
    )
    # Intent Preview State: pass proposed_plan (Draft Itinerary) and orchestrator_state to frontend
    # Refinement leak: show purged checklist immediately after "no [X]"
    proposed_plan = (state.get("purged_proposed_plan") if state else None) or (intent_data or {}).get("proposed_plan")
    if proposed_plan:
        out["data"]["proposed_plan"] = proposed_plan
    if state.get("orchestrator_state"):
        out["data"]["orchestrator_state"] = state["orchestrator_state"]
    planner_msg = state.get("planner_complete_message", "").strip()
    if planner_msg:
        out["planner_complete_message"] = planner_msg
    if last_suggestion:
        out["last_suggestion"] = last_suggestion
    # Persist refinement at service level (DB) so next turn keeps "no limo" etc. without client sending it
    if state.get("purged_proposed_plan") or state.get("purged_search_queries"):
        out["data"]["refinement_context"] = {
            "proposed_plan": state.get("purged_proposed_plan"),
            "search_queries": state.get("purged_search_queries"),
        }
        if thread_id:
            try:
                from db import set_thread_refinement_context
                set_thread_refinement_context(
                    thread_id,
                    proposed_plan=state.get("purged_proposed_plan"),
                    search_queries=state.get("purged_search_queries"),
                )
            except Exception:
                pass
    elif thread_id:
        try:
            from db import set_thread_refinement_context
            set_thread_refinement_context(thread_id, proposed_plan=None, search_queries=None)
        except Exception:
            pass
    # Pass through so chat can use same LLM config for engagement (avoids "no LLM client" when config is valid for planner)
    if llm_config:
        out["llm_config"] = llm_config
    return out


async def _direct_flow(
    user_message: str,
    *,
    user_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    limit: int = 20,
    resolve_intent_fn=None,
    discover_products_fn=None,
) -> Dict[str, Any]:
    """Direct flow without agentic planning (original intent → discover)."""
    if not resolve_intent_fn or not discover_products_fn:
        return {"error": "Services not configured"}

    intent_response = await resolve_intent_fn(user_message)
    intent_data = intent_response.get("data", intent_response)
    intent_type = intent_data.get("intent_type", "unknown")
    # Empty/generic → "browse" (Discovery returns sample products)
    search_query = intent_data.get("search_query") or "browse"

    products_data = None
    adaptive_card = None
    machine_readable = None

    if intent_type == "discover_composite":
        sq = intent_data.get("search_queries") or []
        if sq:
            exp_name = intent_data.get("experience_name") or "experience"
            location = _extract_location(intent_data)
            fulfillment_hints = _extract_fulfillment_hints(intent_data, user_message)
            composed = await _discover_composite(
                search_queries=sq,
                experience_name=exp_name,
                discover_products_fn=discover_products_fn,
                limit=limit,
                location=location,
                fulfillment_hints=fulfillment_hints,
            )
            products_data = composed.get("data")
            adaptive_card = composed.get("adaptive_card")
            machine_readable = composed.get("machine_readable")
            # OrchestrationTrace: product discovery (direct flow, composite)
            pc = (products_data or {}).get("products") or []
            try:
                from db import log_orchestration_trace
                products_meta = [
                    {"product_id": str(p.get("id", "")), "partner_id": str(p.get("partner_id", "") or ""),
                     "protocol": (p.get("source") or "DB").upper(), "relevance_score": 1.0, "admin_weight": 1.0}
                    for p in pc if isinstance(p, dict) and p.get("id")
                ]
                if products_meta:
                    log_orchestration_trace("product_discovery", thread_id=thread_id, user_id=user_id,
                        experience_name=exp_name, metadata={"products": products_meta})
            except Exception:
                pass
            # OrchestrationTrace: bundle created (direct flow, composite)
            bundles = (products_data or {}).get("suggested_bundle_options") or []
            if bundles:
                try:
                    from db import log_orchestration_trace
                    trace_options = [{"label": b.get("label"), "products": [{"product_id": pid, "protocol": "DB", "relevance_score": 1.0, "admin_weight": 1.0} for pid in (b.get("product_ids") or [])]} for b in bundles]
                    if trace_options:
                        log_orchestration_trace("bundle_created", thread_id=thread_id, user_id=user_id,
                            experience_name=exp_name, metadata={"options": trace_options})
                except Exception:
                    pass
    elif intent_type == "discover":
        location = _extract_location(intent_data)
        discovery_response = await discover_products_fn(
            query=search_query,
            limit=limit,
            location=location,
        )
        products_data = discovery_response.get("data", discovery_response)
        adaptive_card = discovery_response.get("adaptive_card")
        machine_readable = discovery_response.get("machine_readable")
        # OrchestrationTrace: product discovery (direct flow)
        pc = (products_data or {}).get("products") or []
        try:
            from db import log_orchestration_trace
            products_meta = [
                {"product_id": str(p.get("id", "")), "partner_id": str(p.get("partner_id", "") or ""),
                 "protocol": (p.get("source") or "DB").upper(), "relevance_score": 1.0, "admin_weight": 1.0}
                for p in pc if isinstance(p, dict) and p.get("id")
            ]
            if products_meta:
                log_orchestration_trace("product_discovery", thread_id=thread_id, user_id=user_id,
                    query=search_query, metadata={"products": products_meta})
        except Exception:
            pass

    return _build_response(
        intent_data=intent_data,
        products_data=products_data,
        adaptive_card=adaptive_card,
        machine_readable=machine_readable,
        agent_reasoning=[],
        user_message=user_message,
    )


# Orchestrator states for context-aware planning
ORCHESTRATOR_STATE_AWAITING_PROBE = "AWAITING_PROBE"


def _has_location_or_time(
    intent_data: Optional[Dict[str, Any]],
    user_message: Optional[str] = None,
) -> bool:
    """Return True only if we have BOTH location AND time for composite (Halt & Preview until both are present)."""
    if not intent_data:
        return False
    loc = _extract_location(intent_data)
    has_location = bool(loc and str(loc).strip())
    if not has_location:
        for e in intent_data.get("entities", []):
            if isinstance(e, dict) and (e.get("type") or "").lower() == "location" and e.get("value"):
                has_location = True
                break
    has_time = False
    hints = _extract_fulfillment_hints(intent_data, user_message)
    if hints and (hints.get("pickup_time") or hints.get("pickup_address")):
        has_time = True
    for e in intent_data.get("entities", []):
        if isinstance(e, dict):
            t = (e.get("type") or "").lower()
            if t in ("time", "date") and e.get("value"):
                has_time = True
                break
    return has_location and has_time


def _is_outdoor_experience(experience_name: str, search_queries: Optional[List[str]]) -> bool:
    """Return True if experience is outdoor/location-based (picnic, date night, etc.)."""
    name = (experience_name or "").lower()
    outdoor_keywords = ("picnic", "outdoor", "garden", "park", "beach", "rooftop")
    if any(k in name for k in outdoor_keywords):
        return True
    qs = " ".join(str(s).lower() for s in (search_queries or []))
    if any(k in qs for k in outdoor_keywords):
        return True
    return False


def _pivot_outdoor_to_indoor(
    search_queries: List[str],
    bundle_options: Optional[List[Dict[str, Any]]],
) -> tuple:
    """Swap outdoor categories (e.g. picnic) for indoor when weather is rain. Returns (queries, options)."""
    pivot_map = {
        "picnic": "indoor dining",
        "outdoor": "indoor",
        "garden": "indoor dining",
        "park": "indoor",
        "beach": "indoor",
    }
    new_queries = []
    for q in search_queries or []:
        ql = str(q).lower()
        replaced = False
        for outdoor, indoor in pivot_map.items():
            if outdoor in ql:
                new_queries.append(indoor)
                replaced = True
                break
        if not replaced:
            new_queries.append(q)
    new_opts = []
    for opt in bundle_options or []:
        if not isinstance(opt, dict):
            new_opts.append(opt)
            continue
        cats = opt.get("categories") or []
        new_cats = []
        for c in cats:
            cl = str(c).lower()
            replaced = False
            for outdoor, indoor in pivot_map.items():
                if outdoor in cl:
                    new_cats.append(indoor)
                    replaced = True
                    break
            if not replaced:
                new_cats.append(c)
        new_opts.append({**opt, "categories": new_cats})
    return (new_queries or search_queries, new_opts or bundle_options)


def _extract_location(intent_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extract location from intent entities."""
    if not intent_data:
        return None
    for e in intent_data.get("entities", []):
        if isinstance(e, dict) and e.get("type") == "location":
            return str(e.get("value", "")) or None
    return None


def _extract_budget(intent_data: Optional[Dict[str, Any]]) -> Optional[int]:
    """Extract budget in cents from intent entities."""
    if not intent_data:
        return None
    for e in intent_data.get("entities", []):
        if isinstance(e, dict) and e.get("type") == "budget":
            v = e.get("value")
            if v is not None:
                try:
                    return int(v)
                except (TypeError, ValueError):
                    pass
    return None


def _extract_fulfillment_hints(
    intent_data: Optional[Dict[str, Any]],
    user_message: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """Extract pickup_time, pickup_address, delivery_address from intent entities or user message."""
    hints: Dict[str, str] = {}
    if intent_data:
        for e in intent_data.get("entities", []):
            if isinstance(e, dict):
                t = (e.get("type") or "").lower()
                v = e.get("value")
                if t and v is not None:
                    vstr = str(v).strip()
                    if t == "pickup_time" and vstr:
                        hints["pickup_time"] = vstr
                    elif t == "pickup_address" and vstr:
                        hints["pickup_address"] = vstr
                    elif t == "delivery_address" and vstr:
                        hints["delivery_address"] = vstr
    if user_message and len(hints) < 3:
        msg = (user_message or "").strip()
        if not hints.get("pickup_time"):
            # e.g. "6 PM", "6:00", "6pm", "tonight", "at 7"
            m = re.search(
                r"(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?|tonight|this evening)",
                msg,
                re.I,
            )
            if m:
                hints["pickup_time"] = m.group(1).strip()
        if not hints.get("pickup_address"):
            # "pick me up at X", "pickup at X", "from X"
            m = re.search(
                r"(?:pick\s*(?:me\s*)?up\s*(?:at|from)\s*|pickup\s*(?:at|from)\s*|from\s+)([^,]+?)(?:\s*,|\s+deliver|\s+to\s|$)",
                msg,
                re.I,
            )
            if m:
                hints["pickup_address"] = m.group(1).strip()
        if not hints.get("delivery_address"):
            # "deliver to X", "delivery to X", "at the X"
            m = re.search(
                r"(?:deliver\s*(?:to|at)\s*|delivery\s*(?:to|at)\s*|to\s+)([^,]+?)(?:\s*,|$)",
                msg,
                re.I,
            )
            if m:
                hints["delivery_address"] = m.group(1).strip()
    return hints if hints else None


def _format_step_key(step: str) -> str:
    """Convert step key like 'before_discover_composite' to 'Before discover composite' for display."""
    return step.replace("_", " ").title()


def _thinking_message(step: str, context: Dict[str, Any], overrides: Optional[Dict[str, str]] = None) -> str:
    """Derive dynamic thinking message from step and current state. Admin overrides from platform_config.thinking_messages take precedence."""
    templates = {
        "intent_resolved": "Understanding what you're looking for...",
        "before_complete_probing": "Let me ask a few questions to tailor this...",
        "before_handle_unrelated": "I'd be happy to show you options! Let me put something together...",
        "before_weather": "Looking up weather for {location}...",
        "after_weather": None,  # Dynamic from weather_desc
        "before_occasions": "Checking what's happening in {location}...",
        "before_discover_products": "Looking for the best {query}...",
        "before_discover_composite": "Looking for the best options for your {experience_name}...",
        "after_discover": "Wow, look at all the options we have, let me pick the best...",
        "before_bundle": "Curating your perfect bundle...",
        "before_response": "Putting it all together...",
    }
    raw = (overrides or {}).get(step) or templates.get(step)
    # If override is empty or equals the raw step key (e.g. "before_discover_composite"), use template
    if not raw or raw.strip() == step:
        msg = templates.get(step)
    else:
        msg = raw
    if msg is None and step == "after_weather":
        desc = (context.get("weather_desc") or "").lower()
        if any(w in desc for w in ("rain", "storm", "snow", "chilly", "cold")):
            return "Looks chilly next week - maybe pick a different day?"
        return "Looks perfect for outdoor plans!"
    if msg is None:
        return _format_step_key(step) + "..."
    loc = context.get("location") or "your area"
    query = context.get("query") or context.get("search_query") or "options"
    exp = context.get("experience_name") or "experience"
    step_display = _format_step_key(step)
    try:
        return msg.format(location=loc, query=query, experience_name=exp, step=step_display)
    except (KeyError, ValueError):
        return msg


async def _emit_thinking(
    on_thinking: Optional[Callable[[str, Optional[Dict]], Awaitable[None]]],
    step: str,
    context: Dict[str, Any],
    thinking_messages: Optional[Dict[str, str]] = None,
) -> None:
    """Emit thinking message if callback provided. Uses platform_config.thinking_messages overrides when set."""
    if on_thinking:
        msg = _thinking_message(step, context, thinking_messages)
        await on_thinking(msg, {"step": step, **context})


def _build_response(
    *,
    intent_data: Optional[Dict[str, Any]] = None,
    products_data: Optional[Dict[str, Any]] = None,
    adaptive_card: Optional[Dict[str, Any]] = None,
    machine_readable: Optional[Dict[str, Any]] = None,
    agent_reasoning: Optional[list] = None,
    user_message: str = "",
    error: Optional[str] = None,
    engagement_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build unified chat response."""
    intent_data = intent_data or {}
    search_query = intent_data.get("search_query") or user_message[:100]

    mr = {
        "@context": "https://schema.org",
        "@type": "ChatOrchestrationResult",
        "intent": {
            "@type": "Intent",
            "intentType": intent_data.get("intent_type", "unknown"),
            "searchQuery": search_query,
            "confidenceScore": intent_data.get("confidence_score"),
        },
        "products": machine_readable,
    }
    if agent_reasoning:
        mr["agentReasoning"] = agent_reasoning

    out = {
        "data": {
            "intent": intent_data,
            "products": products_data,
        },
        "machine_readable": mr,
        "adaptive_card": adaptive_card,
        "agent_reasoning": agent_reasoning or [],
    }
    if engagement_data:
        out["data"]["engagement"] = engagement_data
    if error:
        out["data"]["error"] = error
        out["error"] = error
    return out
