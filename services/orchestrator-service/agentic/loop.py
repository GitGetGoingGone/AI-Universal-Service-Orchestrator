"""Agentic decision loop: Observe → Reason → Plan → Execute → Reflect."""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

from clients import get_bundle_details, get_order_status
from .planner import plan_next_action
from .tools import execute_tool

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 15.0


def _get_llm_config() -> Dict[str, Any]:
    from api.admin import get_llm_config
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
) -> Dict[str, Any]:
    """Call discover_products per query, compose experience bundle. When bundle_options provided, build multiple bundles with prices."""
    from packages.shared.adaptive_cards.experience_card import generate_experience_card

    categories: List[Dict[str, Any]] = []
    all_products: List[Dict[str, Any]] = []
    item_list_elements: List[Dict[str, Any]] = []
    suggested_bundle_options: List[Dict[str, Any]] = []

    # Use composite_discovery_config.products_per_category when available (default 3 for curated bundle)
    try:
        from api.admin import get_composite_discovery_config
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
            product_ids: List[str] = []
            total_price = 0.0
            for cat in opt_cats:
                prods = category_products.get(cat, [])
                if prods:
                    p = prods[0]  # Pick first (e.g. best-ranked)
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
                })

    adaptive_card = generate_experience_card(
        experience_name or "experience",
        categories,
        suggested_bundle_options=suggested_bundle_options if suggested_bundle_options else None,
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

    state = {
        "messages": messages or [],
        "last_suggestion": last_suggestion,
        "probe_count": probe_count,
        "last_tool_result": None,
        "iteration": 0,
        "agent_reasoning": [],
        "bundle_id": bundle_id,
        "order_id": order_id,
    }

    intent_data = None
    products_data = None
    adaptive_card = None
    machine_readable = None
    engagement_data: Dict[str, Any] = {}

    llm_config = _get_llm_config()
    if thinking_messages is None:
        try:
            from api.admin import get_thinking_messages
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
                from api.admin import get_upsell_surge_rules
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
            elif rec == "discover_composite" and intent_data.get("intent_type") == "discover_composite":
                plan = {
                    "action": "tool",
                    "tool_name": "discover_composite",
                    "tool_args": {
                        "bundle_options": intent_data.get("bundle_options") or [],
                        "search_queries": intent_data.get("search_queries") or ["flowers", "restaurant", "movies"],
                        "experience_name": intent_data.get("experience_name") or "experience",
                        "location": _extract_location(intent_data),
                        "budget_max": _extract_budget(intent_data),
                    },
                    "reasoning": "Intent recommended discover_composite.",
                }
            elif rec == "discover_products" and intent_data.get("intent_type") in ("discover", "browse"):
                sq = intent_data.get("search_query") or "browse"
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

            if tool_name == "discover_composite" and intent_data and intent_data.get("intent_type") == "discover_composite":
                tool_args = dict(tool_args)
                if not tool_args.get("bundle_options") and intent_data.get("bundle_options"):
                    tool_args["bundle_options"] = intent_data.get("bundle_options")
                if not tool_args.get("search_queries"):
                    tool_args["search_queries"] = intent_data.get("search_queries") or []
                if not tool_args.get("experience_name"):
                    tool_args["experience_name"] = intent_data.get("experience_name") or "experience"
                if not tool_args.get("location") and intent_data:
                    tool_args["location"] = _extract_location(intent_data)
                if not tool_args.get("budget_max") and intent_data:
                    tool_args["budget_max"] = _extract_budget(intent_data)

            async def _discover_composite_fn(search_queries, experience_name, location=None, budget_max=None, bundle_options=None):
                return await _discover_composite(
                    search_queries=search_queries,
                    experience_name=experience_name,
                    discover_products_fn=discover_products_fn,
                    limit=limit,
                    location=location,
                    budget_max=budget_max,
                    bundle_options=bundle_options,
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
                # Don't auto-fetch for discover_composite; let planner decide (probe first or fetch)
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
                # Use intent's bundle_options when already built; else LLM-suggest 2-4 options
                has_intent_bundles = (products_data or {}).get("suggested_bundle_options")
                if has_intent_bundles:
                    engagement_data["suggested_bundle_options"] = has_intent_bundles
                elif products_data and (products_data.get("categories") or products_data.get("products")):
                    await _emit_thinking(on_thinking, "before_bundle", intent_data or {}, thinking_messages or {})
                    try:
                        from api.admin import _get_platform_config
                        cfg = _get_platform_config() or {}
                        if cfg.get("enable_composite_bundle_suggestion", True) is False:
                            pass  # Skip bundle suggestion when disabled
                        else:
                            from agentic.response import suggest_composite_bundle_options
                            categories = products_data.get("categories") or []
                            budget = _extract_budget(intent_data) if intent_data else None
                            options = await suggest_composite_bundle_options(
                                categories=categories,
                                user_message=user_message,
                                experience_name=products_data.get("experience_name", "experience"),
                                budget_max=budget,
                            )
                            if options:
                                engagement_data["suggested_bundle_options"] = options
                                from packages.shared.adaptive_cards.experience_card import generate_experience_card
                                adaptive_card = generate_experience_card(
                                    products_data.get("experience_name", "experience"),
                                    categories,
                                    suggested_bundle_options=options,
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
                                    from packages.shared.adaptive_cards.experience_card import generate_experience_card
                                    adaptive_card = generate_experience_card(
                                        products_data.get("experience_name", "experience"),
                                        categories,
                                        suggested_bundle_product_ids=suggested,
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
    planner_msg = state.get("planner_complete_message", "").strip()
    if planner_msg:
        out["planner_complete_message"] = planner_msg
    if last_suggestion:
        out["last_suggestion"] = last_suggestion
    return out


async def _direct_flow(
    user_message: str,
    *,
    user_id: Optional[str] = None,
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
            composed = await _discover_composite(
                search_queries=sq,
                experience_name=exp_name,
                discover_products_fn=discover_products_fn,
                limit=limit,
                location=location,
            )
            products_data = composed.get("data")
            adaptive_card = composed.get("adaptive_card")
            machine_readable = composed.get("machine_readable")
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

    return _build_response(
        intent_data=intent_data,
        products_data=products_data,
        adaptive_card=adaptive_card,
        machine_readable=machine_readable,
        agent_reasoning=[],
        user_message=user_message,
    )


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
