"""Supabase database client for partner portal."""

from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from config import settings

_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Get Supabase client."""
    global _client
    if _client is not None:
        return _client
    if not settings.supabase_configured:
        return None
    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


async def create_partner(
    business_name: str,
    contact_email: str,
    business_type: Optional[str] = None,
    contact_phone: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create a new partner. user_id omitted for MVP (no auth)."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("partners").insert({
            "business_name": business_name,
            "contact_email": contact_email,
            "business_type": business_type or "retail",
            "contact_phone": contact_phone,
            "verification_status": "pending",
            "is_active": True,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def get_partner_by_id(partner_id: str) -> Optional[Dict[str, Any]]:
    """Get partner by ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partners")
            .select("*")
            .eq("id", partner_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def list_partners(limit: int = 50) -> List[Dict[str, Any]]:
    """List all active partners."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("partners")
            .select("id, business_name, contact_email, business_type, is_active")
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def create_product(
    partner_id: str,
    name: str,
    price: float,
    description: Optional[str] = None,
    currency: str = "USD",
    capabilities: Optional[list] = None,
) -> Optional[Dict[str, Any]]:
    """Create a product for a partner."""
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "partner_id": partner_id,
            "name": name,
            "price": price,
            "currency": currency,
        }
        if description:
            row["description"] = description
        if capabilities:
            row["capabilities"] = capabilities
        result = client.table("products").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def list_products(partner_id: str) -> List[Dict[str, Any]]:
    """List products for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("products")
            .select("id, name, description, price, currency, capabilities")
            .eq("partner_id", partner_id)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def set_partner_webhook(partner_id: str, webhook_url: str) -> Optional[Dict[str, Any]]:
    """
    Set partner webhook URL for change requests.
    Uses communication_preferences with channel='api'.
    """
    client = get_supabase()
    if not client:
        return None
    try:
        # Upsert: delete existing api preference, insert new
        client.table("communication_preferences").delete().eq(
            "partner_id", partner_id
        ).eq("channel", "api").execute()

        result = client.table("communication_preferences").insert({
            "partner_id": partner_id,
            "channel": "api",
            "channel_identifier": webhook_url,
            "is_preferred": True,
            "is_active": True,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


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
