"""Supabase client for Omnichannel Broker."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from supabase import create_client, Client

from config import settings

_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    global _client
    if _client is not None:
        return _client
    if not settings.supabase_configured:
        return None
    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


async def get_partner_webhook(partner_id: str) -> Optional[str]:
    """Get partner webhook URL from communication_preferences."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("communication_preferences")
            .select("channel_identifier")
            .eq("partner_id", partner_id)
            .eq("channel", "api")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0].get("channel_identifier")
        return None
    except Exception:
        return None


async def create_negotiation(
    order_id: str,
    order_leg_id: str,
    partner_id: str,
    negotiation_type: str,
    original_request: Dict[str, Any],
    channel: str = "api",
) -> Optional[Dict[str, Any]]:
    """Create a negotiation record."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("negotiations").insert({
            "order_id": order_id,
            "order_leg_id": order_leg_id,
            "partner_id": partner_id,
            "negotiation_type": negotiation_type,
            "status": "awaiting_partner_reply",
            "channel": channel,
            "original_request": original_request,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def get_negotiation(negotiation_id: str) -> Optional[Dict[str, Any]]:
    """Get negotiation by ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("negotiations")
            .select("*")
            .eq("id", negotiation_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def update_negotiation_status(
    negotiation_id: str,
    status: str,
    response_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """Update negotiation status."""
    client = get_supabase()
    if not client:
        return False
    try:
        update = {"status": status}
        if response_data:
            update["responded_at"] = datetime.now(timezone.utc).isoformat()
        client.table("negotiations").update(update).eq("id", negotiation_id).execute()
        return True
    except Exception:
        return False


async def add_negotiation_message(
    negotiation_id: str,
    message_type: str,
    content: str,
    channel: str = "api",
    metadata: Optional[Dict] = None,
) -> bool:
    """Add a negotiation message."""
    client = get_supabase()
    if not client:
        return False
    try:
        row = {"negotiation_id": negotiation_id, "message_type": message_type, "content": content, "channel": channel}
        if metadata:
            row["metadata"] = metadata
        client.table("negotiation_messages").insert(row).execute()
        return True
    except Exception:
        return False
