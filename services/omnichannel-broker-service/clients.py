"""HTTP clients for Re-Sourcing Service."""

import logging
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


async def trigger_recovery(
    negotiation_id: str,
    rejection_payload: Dict[str, Any],
) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Call Re-Sourcing Service to handle partner rejection.
    Returns (success, response_data).
    """
    url = f"{settings.re_sourcing_service_url.rstrip('/')}/api/v1/recovery/trigger"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                url,
                json={"negotiation_id": negotiation_id, "rejection": rejection_payload},
            )
            if r.is_success:
                return True, r.json() if r.content else {}
            logger.warning("Re-Sourcing trigger failed: %s %s", r.status_code, r.text[:200])
            return False, None
    except Exception as e:
        logger.exception("Re-Sourcing trigger error: %s", e)
        return False, None
