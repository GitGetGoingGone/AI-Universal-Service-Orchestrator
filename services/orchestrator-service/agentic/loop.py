"""Agentic decision loop: Observe → Reason → Plan → Execute → Reflect."""

import logging
from typing import Any, Dict, List, Optional

import httpx

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
) -> Dict[str, Any]:
    """Call discover_products per query, compose experience bundle."""
    from packages.shared.adaptive_cards.experience_card import generate_experience_card

    categories: List[Dict[str, Any]] = []
    all_products: List[Dict[str, Any]] = []
    item_list_elements: List[Dict[str, Any]] = []

    # Use composite_discovery_config.products_per_category when available
    try:
        from api.admin import get_composite_discovery_config
        cdc = get_composite_discovery_config()
        per_cat = cdc.get("products_per_category")
        if per_cat is not None and isinstance(per_cat, (int, float)):
            per_limit = max(1, min(20, int(per_cat)))
        else:
            per_limit = max(5, limit // len(search_queries)) if search_queries else limit
    except Exception:
        per_limit = max(5, limit // len(search_queries)) if search_queries else limit
    for q in search_queries:
        if not q or not str(q).strip():
            continue
        try:
            resp = await discover_products_fn(
                query=str(q).strip(),
                limit=per_limit,
                location=location,
                partner_id=partner_id,
                budget_max=budget_max,
            )
        except Exception as e:
            logger.warning("Discover composite query %s failed: %s", q, e)
            resp = {"data": {"products": [], "count": 0}}
        products = resp.get("data", resp).get("products", [])
        categories.append({"query": q, "products": products})
        all_products.extend(products)
        for p in products:
            item_list_elements.append({
                "@type": "Product",
                "name": p.get("name", ""),
                "description": p.get("description", ""),
                "offers": {"@type": "Offer", "price": float(p.get("price", 0)), "priceCurrency": p.get("currency", "USD")},
                "identifier": str(p.get("id", "")),
            })

    adaptive_card = generate_experience_card(experience_name or "experience", categories)
    machine_readable = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "numberOfItems": len(all_products),
        "itemListElement": item_list_elements,
    }
    return {
        "data": {
            "experience_name": experience_name or "experience",
            "categories": categories,
            "products": all_products,
            "count": len(all_products),
        },
        "adaptive_card": adaptive_card,
        "machine_readable": machine_readable,
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

    # Derive last_suggestion from conversation history (for refinement: "I don't want flowers, add a movie")
    last_suggestion = None
    if messages:
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "assistant":
                content = m.get("content") or ""
                if content:
                    last_suggestion = str(content)[:500]
                break

    state = {
        "messages": messages or [],
        "last_suggestion": last_suggestion,
        "last_tool_result": None,
        "iteration": 0,
        "agent_reasoning": [],
    }

    intent_data = None
    products_data = None
    adaptive_card = None
    machine_readable = None
    engagement_data: Dict[str, Any] = {}

    llm_config = _get_llm_config()

    for iteration in range(max_iterations):
        state["iteration"] = iteration

        plan = await plan_next_action(
            user_message, state, max_iterations=max_iterations, llm_config=llm_config
        )

        if plan.get("action") == "complete":
            msg = (plan.get("message") or "").strip()
            # Override: if planner said "Done."/empty with no products, and last_suggestion looks like probing,
            # user likely answered our questions—fetch instead of completing
            if (not msg or msg == "Done.") and not products_data and not intent_data:
                ls = (state.get("last_suggestion") or "").lower()
                probe_keywords = ("budget", "dietary", "preferences", "location", "what date", "occasion", "add flowers", "add something", "?")
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

            # Inject last_suggestion for resolve_intent (refinement: "I don't want flowers, add a movie")
            if tool_name == "resolve_intent" and state.get("last_suggestion"):
                tool_args = dict(tool_args)
                tool_args.setdefault("last_suggestion", state["last_suggestion"])

            if tool_name == "create_standing_intent":
                tool_args = dict(tool_args)
                tool_args.setdefault("platform", platform)
                tool_args.setdefault("thread_id", thread_id)

            if tool_name == "discover_composite" and intent_data and intent_data.get("intent_type") == "discover_composite":
                tool_args = dict(tool_args)
                if not tool_args.get("search_queries"):
                    tool_args["search_queries"] = intent_data.get("search_queries") or []
                if not tool_args.get("experience_name"):
                    tool_args["experience_name"] = intent_data.get("experience_name") or "experience"
                if not tool_args.get("location") and intent_data:
                    tool_args["location"] = _extract_location(intent_data)
                if not tool_args.get("budget_max") and intent_data:
                    tool_args["budget_max"] = _extract_budget(intent_data)

            async def _discover_composite_fn(search_queries, experience_name, location=None, budget_max=None):
                return await _discover_composite(
                    search_queries=search_queries,
                    experience_name=experience_name,
                    discover_products_fn=discover_products_fn,
                    limit=limit,
                    location=location,
                    budget_max=budget_max,
                )

            result = await execute_tool(
                tool_name,
                tool_args,
                resolve_intent_fn=resolve_intent_fn,
                discover_products_fn=discover_products_fn,
                discover_composite_fn=_discover_composite_fn,
                start_orchestration_fn=start_orchestration_fn,
                create_standing_intent_fn=create_standing_intent_fn,
                web_search_fn=_web_search,
                get_weather_fn=_get_weather,
                get_upcoming_occasions_fn=_get_upcoming_occasions,
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
            elif tool_name == "get_upcoming_occasions":
                engagement_data["occasions"] = result.get("data", result)
            elif tool_name == "discover_composite":
                products_data = result.get("data", result)
                adaptive_card = result.get("adaptive_card")
                machine_readable = result.get("machine_readable")
                # LLM-suggested bundle options: 2-4 options, each one product per category (when enabled)
                if products_data and (products_data.get("categories") or products_data.get("products")):
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
            elif tool_name == "create_standing_intent":
                intent_data = intent_data or {}
                intent_data["standing_intent"] = result
            elif tool_name == "complete":
                summary = (result.get("summary") or "").strip()
                if summary:
                    state["planner_complete_message"] = summary
                break

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
