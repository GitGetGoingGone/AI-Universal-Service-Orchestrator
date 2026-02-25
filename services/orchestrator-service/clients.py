"""HTTP clients for Intent and Discovery services."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from config import settings
from db import store_masked_id
from packages.shared.adaptive_cards import generate_product_card
from packages.shared.discovery import fallback_search_query
from packages.shared.gateway_signature import sign_request
from packages.shared.json_ld import product_list_ld
from registry import AgentEntry, get_agents

logger = logging.getLogger(__name__)


def _gateway_headers_for_discovery(method: str, path: str, body: bytes = b"") -> Dict[str, str]:
    """When GATEWAY_INTERNAL_SECRET is set, return X-Gateway-Signature and X-Gateway-Timestamp for Discovery requests."""
    if not getattr(settings, "gateway_internal_secret", ""):
        return {}
    sig, ts = sign_request(method, path, body, settings.gateway_internal_secret)
    return {"X-Gateway-Signature": sig, "X-Gateway-Timestamp": str(ts)}

# Render cold starts can take 30-60s; use 60s timeout for staging
HTTP_TIMEOUT = 60.0


async def discover_products_via_rpc(
    base_url: str,
    query: str,
    limit: int = 20,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
    experience_tag: Optional[str] = None,
    experience_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Call a Business Agent (Discovery) via JSON-RPC 2.0 discovery/search.
    base_url: agent base URL (e.g. from RegistryDriver). Returns {"products": [...], "count": N} or raises.
    """
    path = "/api/v1/ucp/rpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "discovery/search",
        "params": {
            "query": query,
            "limit": limit,
        },
        "id": 1,
    }
    if partner_id:
        payload["params"]["filter_partner_id"] = partner_id
    if exclude_partner_id:
        payload["params"]["exclude_partner_id"] = exclude_partner_id
    if experience_tag:
        payload["params"]["experience_tag"] = experience_tag
    if experience_tags:
        payload["params"]["experience_tags"] = experience_tags

    import json
    body_bytes = json.dumps(payload).encode("utf-8")
    url = f"{base_url.rstrip('/')}{path}"
    headers = _gateway_headers_for_discovery("POST", path, body_bytes)
    headers["Content-Type"] = "application/json"

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, content=body_bytes, headers=headers)
        r.raise_for_status()
        data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "JSON-RPC error"))
    result = data.get("result") or {}
    return result


async def get_experience_categories() -> List[str]:
    """
    Fetch available experience categories from Discovery (GET /api/v1/experience-categories).
    Used to pre-fill intent resolve so the LLM knows available tags for theme bundles.
    Returns empty list if Discovery is unavailable or endpoint errors.
    """
    url = f"{settings.discovery_service_url}/api/v1/experience-categories"
    path = "/api/v1/experience-categories"
    headers = _gateway_headers_for_discovery("GET", path)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            data = r.json()
        inner = data.get("data") or data
        cats = inner.get("experience_categories")
        if isinstance(cats, list):
            return [str(t).strip() for t in cats if t and str(t).strip()]
        return []
    except Exception as e:
        logger.debug("Could not fetch experience categories from Discovery: %s", e)
        return []


async def discover_products_broadcast(
    query: str,
    limit: int = 20,
    location: Optional[str] = None,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
    budget_max: Optional[int] = None,
    experience_tag: Optional[str] = None,
    experience_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Broadcast discovery: fan out to all agents with discovery capability via JSON-RPC,
    merge results (dedupe by id), return same shape as discover_products.
    When ID_MASKING_ENABLED=true, product ids are masked as uso_{agent_slug}_{short_id} and stored in id_masking_map with TTL; resolve at checkout.
    """
    agents = get_agents(capability="discovery")
    if not agents:
        return await discover_products(
            query=query,
            limit=limit,
            location=location,
            partner_id=partner_id,
            exclude_partner_id=exclude_partner_id,
            budget_max=budget_max,
            experience_tag=experience_tag,
            experience_tags=experience_tags,
        )

    async def one_agent(entry: AgentEntry) -> tuple:
        """Return (agent_slug, products) for merging and optional masking."""
        try:
            r = await discover_products_via_rpc(
                entry.base_url,
                query=query,
                limit=limit,
                partner_id=partner_id,
                exclude_partner_id=exclude_partner_id,
                experience_tag=experience_tag,
                experience_tags=experience_tags,
            )
            products = (r.get("products") or [])[:limit]
            return (entry.slug, products)
        except Exception as e:
            logger.warning("Discovery RPC failed for %s: %s", entry.base_url, e)
            return (entry.slug, [])

    tasks = [one_agent(a) for a in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    merged: List[Dict[str, Any]] = []
    seen_ids: set = set()
    id_masking_enabled = getattr(settings, "id_masking_enabled", False)
    for raw in results:
        if isinstance(raw, Exception):
            continue
        slug, product_list = raw if isinstance(raw, tuple) and len(raw) == 2 else ("agent", [])
        for p in product_list:
            if not isinstance(p, dict):
                continue
            p = dict(p)
            pid = p.get("id")
            if id_masking_enabled and pid and slug:
                masked = store_masked_id(slug, str(pid), p.get("partner_id"), "rpc")
                if masked:
                    p["id"] = masked
                p.pop("partner_id", None)
            if pid is not None and str(p.get("id")) not in seen_ids:
                seen_ids.add(str(p.get("id")))
                merged.append(p)
            elif pid is None:
                merged.append(p)
    merged = merged[:limit]
    if budget_max is not None:
        filtered = [p for p in merged if p.get("price") is None or int(round(float(p["price"]) * 100)) <= budget_max]
        merged = filtered[:limit]

    # Fallback: when UCP agents returned no products (e.g. 503), try legacy Discovery REST API
    if not merged and getattr(settings, "discovery_service_url", "").strip():
        try:
            legacy = await discover_products(
                query=query,
                limit=limit,
                location=location,
                partner_id=partner_id,
                exclude_partner_id=exclude_partner_id,
                budget_max=budget_max,
                experience_tag=experience_tag,
                experience_tags=experience_tags,
            )
            inner = legacy.get("data") or legacy
            products_list = inner.get("products") if isinstance(inner, dict) else []
            if isinstance(products_list, list) and products_list:
                merged = products_list[:limit]
                logger.info("Discovery fallback: legacy /discover returned %d products for %s", len(merged), query)
        except Exception as e:
            logger.debug("Discovery fallback (legacy /discover) failed: %s", e)

    item_list_ld = product_list_ld(merged, count=len(merged))
    return {
        "data": {"products": merged, "count": len(merged)},
        "machine_readable": item_list_ld,
        "adaptive_card": generate_product_card(merged[:5]),
        "metadata": {"api_version": "v1", "timestamp": datetime.utcnow().isoformat() + "Z"},
    }


async def resolve_intent_with_fallback(
    text: str,
    user_id: Optional[str] = None,
    last_suggestion: Optional[str] = None,
    recent_conversation: Optional[List[Dict[str, Any]]] = None,
    probe_count: Optional[int] = None,
    thread_context: Optional[Dict[str, Any]] = None,
    force_model: bool = False,
) -> Dict[str, Any]:
    """
    Resolve intent via Intent service. On 502/timeout/unavailable, use local fallback
    so chat still returns products (Intent service outage resilience).
    When force_model=True (ChatGPT/Gemini with force_model_based_intent), do not fall back.
    Automatically fetches experience_categories from Discovery and passes to Intent for theme-bundle prompts.
    """
    experience_categories: List[str] = []
    if getattr(settings, "discovery_service_url", None):
        experience_categories = await get_experience_categories()
    try:
        return await resolve_intent(
            text,
            user_id=user_id,
            last_suggestion=last_suggestion,
            recent_conversation=recent_conversation,
            probe_count=probe_count,
            thread_context=thread_context,
            experience_categories=experience_categories,
            force_model=force_model,
        )
    except (httpx.HTTPStatusError, httpx.RequestError, RuntimeError) as e:
        if force_model:
            raise
        logger.warning("Intent service unavailable (%s), using local fallback", e)
        query = fallback_search_query(text)
        return {
            "data": {
                "intent_id": None,
                "intent_type": "discover",
                "search_query": query,
                "entities": [],
                "confidence_score": 0.5,
                "recommended_next_action": "discover_products",
            },
            "metadata": {"fallback": True, "reason": str(e)},
        }


async def resolve_intent(
    text: str,
    user_id: Optional[str] = None,
    last_suggestion: Optional[str] = None,
    recent_conversation: Optional[List[Dict[str, Any]]] = None,
    probe_count: Optional[int] = None,
    thread_context: Optional[Dict[str, Any]] = None,
    experience_categories: Optional[List[str]] = None,
    force_model: bool = False,
) -> Dict[str, Any]:
    """
    Call Intent service to resolve intent from natural language.
    Raises on 4xx/5xx. Callers should catch and use local fallback when Intent is unavailable.
    When force_model=True, intent service will not fall back to heuristics on LLM failure.
    experience_categories: optional list of experience tags (from GET experience-categories) for theme bundle options.
    """
    url = f"{settings.intent_service_url}/api/v1/resolve"
    payload: Dict[str, Any] = {"text": text, "user_id": user_id, "persist": True}
    if last_suggestion:
        payload["last_suggestion"] = last_suggestion
    if recent_conversation:
        payload["recent_conversation"] = recent_conversation
    if probe_count is not None:
        payload["probe_count"] = probe_count
    if thread_context:
        payload["thread_context"] = thread_context
    if experience_categories:
        payload["experience_categories"] = experience_categories
    if force_model:
        payload["force_model"] = True
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        return r.json()


# Retry 429 from Discovery (e.g. Render free-tier rate limits): max attempts, base delay seconds
DISCOVERY_RETRY_ATTEMPTS = 4
DISCOVERY_RETRY_BASE_DELAY = 20


def _empty_discovery_fallback(query: str) -> Dict[str, Any]:
    """Return empty discovery result when rate limited or unavailable."""
    return {
        "data": {"products": [], "count": 0},
        "machine_readable": {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "numberOfItems": 0,
            "itemListElement": [],
        },
        "adaptive_card": {"type": "AdaptiveCard", "version": "1.5", "body": []},
        "metadata": {"api_version": "v1", "rate_limited": True},
    }


async def discover_products(
    query: str,
    limit: int = 20,
    location: Optional[str] = None,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
    budget_max: Optional[int] = None,
    experience_tag: Optional[str] = None,
    experience_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Call Discovery service to find products by query. Retries on 429 (rate limit)."""
    url = f"{settings.discovery_service_url}/api/v1/discover"
    params: Dict[str, Any] = {"intent": query, "limit": limit}
    if location:
        params["location"] = location
    if partner_id:
        params["partner_id"] = partner_id
    if exclude_partner_id:
        params["exclude_partner_id"] = exclude_partner_id
    if budget_max is not None:
        params["budget_max"] = budget_max
    if experience_tag:
        params["experience_tag"] = experience_tag
    if experience_tags:
        params["experience_tags"] = experience_tags
    path = "/api/v1/discover"
    headers = _gateway_headers_for_discovery("GET", path)
    for attempt in range(DISCOVERY_RETRY_ATTEMPTS):
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.get(url, params=params, headers=headers)
            if r.status_code == 429 and attempt < DISCOVERY_RETRY_ATTEMPTS - 1:
                delay = DISCOVERY_RETRY_BASE_DELAY
                retry_after = r.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = min(60, max(5, int(retry_after)))
                logger.warning(
                    "Discovery rate limited (429), retry %s/%s in %ss",
                    attempt + 1,
                    DISCOVERY_RETRY_ATTEMPTS,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            if r.status_code == 429:
                logger.warning("Discovery rate limited (429) after %s retries, returning empty", DISCOVERY_RETRY_ATTEMPTS)
                return _empty_discovery_fallback(query)
            r.raise_for_status()
            return r.json()

    return _empty_discovery_fallback(query)


async def get_product_details(product_id: str) -> Dict[str, Any]:
    """Call Discovery service to get product by ID (View Details)."""
    url = f"{settings.discovery_service_url}/api/v1/products/{product_id}"
    path = f"/api/v1/products/{product_id}"
    headers = _gateway_headers_for_discovery("GET", path)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.json()


async def get_bundle_details(bundle_id: str) -> Dict[str, Any]:
    """Call Discovery service to get bundle by ID (View Bundle)."""
    url = f"{settings.discovery_service_url}/api/v1/bundles/{bundle_id}"
    path = f"/api/v1/bundles/{bundle_id}"
    headers = _gateway_headers_for_discovery("GET", path)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.json()


async def add_to_bundle(
    product_id: str,
    user_id: Optional[str] = None,
    bundle_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Discovery service to add product to bundle."""
    url = f"{settings.discovery_service_url}/api/v1/bundle/add"
    headers = _gateway_headers_for_discovery("POST", "/api/v1/bundle/add")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            url,
            json={
                "product_id": product_id,
                "user_id": user_id,
                "bundle_id": bundle_id,
            },
            headers=headers,
        )
        r.raise_for_status()
        return r.json()


async def add_to_bundle_bulk(
    product_ids: list[str],
    user_id: Optional[str] = None,
    bundle_id: Optional[str] = None,
    pickup_time: Optional[str] = None,
    pickup_address: Optional[str] = None,
    delivery_address: Optional[str] = None,
    fulfillment_fields: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Call Discovery service to add multiple products to bundle."""
    url = f"{settings.discovery_service_url}/api/v1/bundle/add-bulk"
    payload: Dict[str, Any] = {
        "product_ids": product_ids,
        "user_id": user_id,
        "bundle_id": bundle_id,
    }
    if pickup_time is not None:
        payload["pickup_time"] = pickup_time
    if pickup_address is not None:
        payload["pickup_address"] = pickup_address
    if delivery_address is not None:
        payload["delivery_address"] = delivery_address
    if fulfillment_fields is not None:
        payload["fulfillment_fields"] = fulfillment_fields
    headers = _gateway_headers_for_discovery("POST", "/api/v1/bundle/add-bulk")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()


async def replace_in_bundle(
    bundle_id: str,
    leg_id: str,
    new_product_id: str,
) -> Dict[str, Any]:
    """Replace a product in bundle (category refinement)."""
    url = f"{settings.discovery_service_url}/api/v1/bundle/replace"
    headers = _gateway_headers_for_discovery("POST", "/api/v1/bundle/replace")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            url,
            json={
                "bundle_id": bundle_id,
                "leg_id": leg_id,
                "new_product_id": new_product_id,
            },
            headers=headers,
        )
        r.raise_for_status()
        return r.json()


async def remove_from_bundle(item_id: str) -> Dict[str, Any]:
    """Call Discovery service to remove item from bundle."""
    url = f"{settings.discovery_service_url}/api/v1/bundle/remove"
    headers = _gateway_headers_for_discovery("POST", "/api/v1/bundle/remove")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json={"item_id": item_id}, headers=headers)
        r.raise_for_status()
        return r.json()


async def get_order_status(order_id: str) -> Dict[str, Any]:
    """Call Discovery service to get order status. For track_order tool."""
    url = f"{settings.discovery_service_url}/api/v1/orders/{order_id}/status"
    path = f"/api/v1/orders/{order_id}/status"
    headers = _gateway_headers_for_discovery("GET", path)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code == 404:
            return {"error": "Order not found"}
        r.raise_for_status()
        return r.json()


async def proceed_to_checkout(bundle_id: str) -> Dict[str, Any]:
    """Call Discovery service to proceed to checkout with bundle. Creates order, returns order_id."""
    url = f"{settings.discovery_service_url}/api/v1/checkout"
    headers = _gateway_headers_for_discovery("POST", "/api/v1/checkout")
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json={"bundle_id": bundle_id}, headers=headers)
        r.raise_for_status()
        return r.json()


async def create_payment_intent(order_id: str) -> Dict[str, Any]:
    """Call Payment service to create Stripe PaymentIntent for order."""
    url = f"{settings.payment_service_url}/api/v1/payment/create"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json={"order_id": order_id})
        r.raise_for_status()
        return r.json()


async def confirm_payment(order_id: str) -> Dict[str, Any]:
    """Call Payment service to confirm payment (demo mode). Marks order as paid."""
    url = f"{settings.payment_service_url}/api/v1/payment/confirm"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json={"order_id": order_id})
        r.raise_for_status()
        return r.json()


async def create_change_request(
    order_id: str,
    order_leg_id: str,
    partner_id: str,
    original_item: Dict[str, Any],
    requested_change: Dict[str, Any],
    respond_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Omnichannel Broker to create change request and notify partner."""
    url = f"{settings.omnichannel_broker_url}/api/v1/change-request"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            url,
            json={
                "order_id": order_id,
                "order_leg_id": order_leg_id,
                "partner_id": partner_id,
                "original_item": original_item,
                "requested_change": requested_change,
                "respond_by": respond_by,
            },
        )
        r.raise_for_status()
        return r.json()


async def start_orchestration(
    message: str = "Hello from orchestrator",
    wait_event_name: str = "WakeUp",
) -> Dict[str, Any]:
    """Start a Durable Functions orchestration instance. Returns error dict if Durable is unavailable."""
    url = f"{settings.durable_orchestrator_url}/api/orchestrators/base_orchestrator"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json={"message": message, "wait_event_name": wait_event_name},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        return {
            "error": f"Durable Orchestrator unavailable: {e}",
            "statusQueryGetUri": None,
            "message": "Orchestration could not be started. Ensure Durable Functions is running.",
        }


async def start_standing_intent_orchestration(
    message: str,
    approval_timeout_hours: int = 24,
    platform: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Start standing intent orchestrator. Returns instance ID or error."""
    url = f"{settings.durable_orchestrator_url}/api/orchestrators/standing_intent_orchestrator"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json={
                    "message": message,
                    "approval_timeout_hours": approval_timeout_hours,
                    "platform": platform,
                    "thread_id": thread_id,
                },
            )
            r.raise_for_status()
            data = r.json()
            instance_id = data.get("id") or data.get("instanceId") or data.get("instance_id")
            return {"id": instance_id, "statusQueryGetUri": data.get("statusQueryGetUri")}
    except Exception as e:
        return {"error": str(e)}


async def raise_orchestrator_event(instance_id: str, event_name: str, event_data: Optional[Dict[str, Any]] = None) -> None:
    """Raise external event to wake a waiting orchestrator."""
    url = f"{settings.durable_orchestrator_url}/api/orchestrators/{instance_id}/raise/{event_name}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json=event_data or {})
        r.raise_for_status()


async def get_orchestrator_status(instance_id: str) -> Optional[Dict[str, Any]]:
    """Get orchestration instance status."""
    url = f"{settings.durable_orchestrator_url}/api/orchestrators/{instance_id}/status"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
    except Exception:
        return None


async def create_standing_intent_via_api(
    intent_description: str,
    approval_timeout_hours: int = 24,
    platform: Optional[str] = None,
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create standing intent via orchestrator API (for agentic flow)."""
    url = f"{settings.orchestrator_base_url}/api/v1/standing-intents"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json={
                    "intent_description": intent_description,
                    "approval_timeout_hours": approval_timeout_hours,
                    "platform": platform,
                    "thread_id": thread_id,
                    "user_id": user_id,
                },
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        return {"error": str(e)}


async def register_thread_mapping(
    platform: str,
    thread_id: str,
    user_id: Optional[str] = None,
    platform_user_id: Optional[str] = None,
) -> bool:
    """Register chat thread mapping for webhook push. Returns True if successful."""
    url = f"{settings.webhook_service_url}/api/v1/webhooks/mappings"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json={
                    "platform": platform,
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "platform_user_id": platform_user_id,
                },
            )
            return r.status_code == 200
    except Exception:
        return False
