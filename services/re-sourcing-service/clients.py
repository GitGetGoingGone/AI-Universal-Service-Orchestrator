"""HTTP client for Discovery Service."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def commitment_cancel(partner_id: str, external_order_id: str, vendor_type: str = "shopify") -> bool:
    """Call Payment service to cancel external order at vendor."""
    from config import settings
    url = f"{settings.payment_service_url.rstrip('/')}/api/v1/commitment/cancel"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json={
                "partner_id": partner_id,
                "external_order_id": external_order_id,
                "vendor_type": vendor_type,
            })
            r.raise_for_status()
            return r.json().get("ok", False)
    except Exception as e:
        logger.exception("Commitment cancel failed: %s", e)
        return False


async def discover_products(
    query: str,
    limit: int = 10,
    exclude_partner_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search for alternative products via Discovery."""
    url = f"{settings.discovery_service_url.rstrip('/')}/api/v1/discover"
    params = {"intent": query, "limit": limit}
    if exclude_partner_id:
        params["exclude_partner_id"] = exclude_partner_id
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("data", {}).get("products", [])
    except Exception as e:
        logger.exception("Discovery search failed: %s", e)
        return []
