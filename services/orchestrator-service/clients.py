"""HTTP clients for Intent and Discovery services."""

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from config import settings
from packages.shared.discovery import fallback_search_query

logger = logging.getLogger(__name__)

# Render cold starts can take 30-60s; use 60s timeout for staging
HTTP_TIMEOUT = 60.0


async def resolve_intent_with_fallback(
    text: str,
    user_id: Optional[str] = None,
    last_suggestion: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve intent via Intent service. On 502/timeout/unavailable, use local fallback
    so chat still returns products (Intent service outage resilience).
    """
    try:
        return await resolve_intent(text, user_id=user_id, last_suggestion=last_suggestion)
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning("Intent service unavailable (%s), using local fallback", e)
        query = fallback_search_query(text)
        return {
            "data": {
                "intent_id": None,
                "intent_type": "discover",
                "search_query": query,
                "entities": [],
                "confidence_score": 0.5,
            },
            "metadata": {"fallback": True, "reason": str(e)},
        }


async def resolve_intent(
    text: str,
    user_id: Optional[str] = None,
    last_suggestion: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call Intent service to resolve intent from natural language.
    Raises on 4xx/5xx. Callers should catch and use local fallback when Intent is unavailable.
    """
    url = f"{settings.intent_service_url}/api/v1/resolve"
    payload: Dict[str, Any] = {"text": text, "user_id": user_id, "persist": True}
    if last_suggestion:
        payload["last_suggestion"] = last_suggestion
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
) -> Dict[str, Any]:
    """Call Discovery service to find products by query. Retries on 429 (rate limit)."""
    url = f"{settings.discovery_service_url}/api/v1/discover"
    params = {"intent": query, "limit": limit}
    if location:
        params["location"] = location
    if partner_id:
        params["partner_id"] = partner_id
    for attempt in range(DISCOVERY_RETRY_ATTEMPTS):
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.get(url, params=params)
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


async def get_product_details(product_id: str) -> Dict[str, Any]:
    """Call Discovery service to get product by ID (View Details)."""
    url = f"{settings.discovery_service_url}/api/v1/products/{product_id}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def get_bundle_details(bundle_id: str) -> Dict[str, Any]:
    """Call Discovery service to get bundle by ID (View Bundle)."""
    url = f"{settings.discovery_service_url}/api/v1/bundles/{bundle_id}"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def add_to_bundle(
    product_id: str,
    user_id: Optional[str] = None,
    bundle_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Discovery service to add product to bundle."""
    url = f"{settings.discovery_service_url}/api/v1/bundle/add"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            url,
            json={
                "product_id": product_id,
                "user_id": user_id,
                "bundle_id": bundle_id,
            },
        )
        r.raise_for_status()
        return r.json()


async def remove_from_bundle(item_id: str) -> Dict[str, Any]:
    """Call Discovery service to remove item from bundle."""
    url = f"{settings.discovery_service_url}/api/v1/bundle/remove"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json={"item_id": item_id})
        r.raise_for_status()
        return r.json()


async def proceed_to_checkout(bundle_id: str) -> Dict[str, Any]:
    """Call Discovery service to proceed to checkout with bundle. Creates order, returns order_id."""
    url = f"{settings.discovery_service_url}/api/v1/checkout"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(url, json={"bundle_id": bundle_id})
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
