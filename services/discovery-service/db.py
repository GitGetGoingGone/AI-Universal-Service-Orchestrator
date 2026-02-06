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
            # Search in name or description (case-insensitive)
            pattern = f"%{query}%"
            q = q.or_(f"name.ilike.{pattern},description.ilike.{pattern}")
        if partner_id:
            q = q.eq("partner_id", partner_id)

        result = q.order("created_at", desc=True).limit(limit).execute()
        return result.data or []
    except Exception:
        return []


async def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Get a single product by ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("products")
            .select("id, name, description, price, currency, capabilities, metadata, partner_id")
            .eq("id", product_id)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def add_product_to_bundle(
    product_id: str,
    user_id: Optional[str] = None,
    bundle_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Add product to bundle. Creates new draft bundle if bundle_id not provided.
    Returns bundle with updated info.
    """
    client = get_supabase()
    if not client:
        return None

    product = await get_product_by_id(product_id)
    if not product:
        return None

    price = float(product.get("price", 0))
    partner_id = product.get("partner_id")

    try:
        if bundle_id:
            # Add to existing bundle
            seq_result = (
                client.table("bundle_legs")
                .select("leg_sequence")
                .eq("bundle_id", bundle_id)
                .order("leg_sequence", desc=True)
                .limit(1)
                .execute()
            )
            next_seq = (seq_result.data[0]["leg_sequence"] + 1) if seq_result.data else 1

            bundle = (
                client.table("bundles")
                .select("*")
                .eq("id", bundle_id)
                .single()
                .execute()
            )
            if not bundle.data:
                return None
            bundle_row = bundle.data
            total = float(bundle_row.get("total_price", 0)) + price

            client.table("bundle_legs").insert({
                "bundle_id": bundle_id,
                "leg_sequence": next_seq,
                "product_id": product_id,
                "partner_id": partner_id,
                "leg_type": "product",
                "price": price,
            }).execute()

            client.table("bundles").update({"total_price": total}).eq("id", bundle_id).execute()

            return {
                "bundle_id": bundle_id,
                "product_added": product.get("name"),
                "total_price": total,
                "currency": bundle_row.get("currency", "USD"),
            }
        else:
            # Create new draft bundle
            bundle_row = {
                "user_id": user_id,
                "bundle_name": "Chat Bundle",
                "total_price": price,
                "currency": product.get("currency", "USD"),
                "status": "draft",
            }
            bundle_result = client.table("bundles").insert(bundle_row).execute()
            if not bundle_result.data:
                return None
            new_bundle_id = bundle_result.data[0]["id"]

            client.table("bundle_legs").insert({
                "bundle_id": new_bundle_id,
                "leg_sequence": 1,
                "product_id": product_id,
                "partner_id": partner_id,
                "leg_type": "product",
                "price": price,
            }).execute()

            return {
                "bundle_id": new_bundle_id,
                "product_added": product.get("name"),
                "total_price": price,
                "currency": product.get("currency", "USD"),
            }
    except Exception:
        return None


async def get_bundle_by_id(bundle_id: str) -> Optional[Dict[str, Any]]:
    """
    Get bundle by ID with items (legs joined to products).
    Returns bundle dict with items array for Adaptive Card.
    """
    client = get_supabase()
    if not client:
        return None
    try:
        bundle_result = (
            client.table("bundles")
            .select("id, user_id, bundle_name, total_price, currency, status, created_at")
            .eq("id", bundle_id)
            .single()
            .execute()
        )
        if not bundle_result.data:
            return None
        bundle = dict(bundle_result.data)

        legs_result = (
            client.table("bundle_legs")
            .select("id, leg_sequence, product_id, price")
            .eq("bundle_id", bundle_id)
            .order("leg_sequence")
            .execute()
        )
        legs = legs_result.data or []

        product_ids = [leg["product_id"] for leg in legs if leg.get("product_id")]
        product_names = {}
        if product_ids:
            products_result = (
                client.table("products")
                .select("id, name, currency")
                .in_("id", product_ids)
                .execute()
            )
            for p in products_result.data or []:
                product_names[str(p["id"])] = p

        currency = bundle.get("currency", "USD")
        items = []
        for leg in legs:
            pid = str(leg.get("product_id", ""))
            p = product_names.get(pid, {})
            items.append({
                "id": str(leg.get("id", "")),
                "product_id": pid,
                "name": p.get("name", "Unknown"),
                "price": float(leg.get("price", 0)),
                "currency": p.get("currency", currency),
            })

        bundle["items"] = items
        bundle["item_count"] = len(items)
        bundle["name"] = bundle.get("bundle_name") or "Your Bundle"
        return bundle
    except Exception:
        return None
