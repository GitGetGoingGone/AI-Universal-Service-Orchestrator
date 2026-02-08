"""HTTP client for Discovery Service."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


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
