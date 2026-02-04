"""Supabase database client for discovery service."""

from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from config import settings


_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Get Supabase client. Returns None if not configured."""
    global _client
    if _client is not None:
        return _client
    if not settings.supabase_configured:
        return None
    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


async def check_connection() -> bool:
    """Verify database connectivity."""
    client = get_supabase()
    if not client:
        return False
    try:
        # Simple query to verify connection
        result = client.table("products").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


async def search_products(
    query: str,
    limit: int = 20,
    partner_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search products by name/description.
    Uses simple text search for MVP; semantic search (pgvector) can be added later.
    """
    client = get_supabase()
    if not client:
        return []

    try:
        # Text search: filter by name containing query (case-insensitive)
        q = (
            client.table("products")
            .select("id, name, description, price, currency, capabilities, metadata, partner_id")
            .is_("deleted_at", "null")
        )

        if query:
            q = q.ilike("name", f"%{query}%")
        if partner_id:
            q = q.eq("partner_id", partner_id)

        result = q.order("created_at", desc=True).limit(limit).execute()
        return result.data or []
    except Exception:
        return []
