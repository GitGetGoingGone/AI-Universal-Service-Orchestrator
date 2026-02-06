"""HTTP clients for Intent and Discovery services."""

from typing import Any, Dict, Optional

import httpx

from config import settings

# Render cold starts can take 30-60s; use 60s timeout for staging
HTTP_TIMEOUT = 60.0


async def resolve_intent(text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Call Intent service to resolve intent from natural language."""
    url = f"{settings.intent_service_url}/api/v1/resolve"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.post(
            url,
            json={"text": text, "user_id": user_id, "persist": True},
        )
        r.raise_for_status()
        return r.json()


async def discover_products(
    query: str,
    limit: int = 20,
    location: Optional[str] = None,
    partner_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Discovery service to find products by query."""
    url = f"{settings.discovery_service_url}/api/v1/discover"
    params = {"intent": query, "limit": limit}
    if location:
        params["location"] = location
    if partner_id:
        params["partner_id"] = partner_id
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(url, params=params)
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
