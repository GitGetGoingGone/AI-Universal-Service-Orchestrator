"""Outbound HTTP to partner webhooks."""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


async def notify_partner(
    webhook_url: str,
    payload: Dict[str, Any],
    timeout: float = 30.0,
) -> tuple[bool, Optional[str]]:
    """
    POST change request to partner webhook.
    Returns (success, error_message).
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(webhook_url, json=payload)
            if r.is_success:
                return True, None
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except httpx.TimeoutException as e:
        logger.warning("Partner webhook timeout: %s", webhook_url)
        return False, str(e)
    except Exception as e:
        logger.exception("Partner webhook error: %s", webhook_url)
        return False, str(e)
