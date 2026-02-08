"""Supabase database client for discovery service."""

import uuid as uuid_module
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from config import settings
from packages.shared.discovery import is_browse_query


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
    exclude_partner_id: Optional[str] = None,
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

        if query and not is_browse_query(query):
            # Search in name or description (case-insensitive)
            # Browse queries (sample, demo, please, etc.) return products without filter
            pattern = f"%{query}%"
            q = q.or_(f"name.ilike.{pattern},description.ilike.{pattern}")
        if partner_id:
            q = q.eq("partner_id", partner_id)
        if exclude_partner_id:
            q = q.neq("partner_id", exclude_partner_id)

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
            # user_id must be a valid UUID referencing users(id); omit if not (e.g. "test-user")
            bundle_user_id = None
            if user_id:
                try:
                    uid = uuid_module.UUID(str(user_id))
                    bundle_user_id = str(uid)
                except (ValueError, TypeError):
                    pass
            bundle_row = {
                "bundle_name": "Chat Bundle",
                "total_price": price,
                "currency": product.get("currency", "USD"),
                "status": "draft",
            }
            if bundle_user_id:
                bundle_row["user_id"] = bundle_user_id
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


async def create_order_from_bundle(bundle_id: str) -> Optional[Dict[str, Any]]:
    """
    Create order from bundle. Inserts into orders, order_items, order_legs.
    Returns order dict with id, bundle_id, total_amount, currency, status, line_items.
    """
    client = get_supabase()
    if not client:
        return None
    try:
        bundle = await get_bundle_by_id(bundle_id)
        if not bundle:
            return None
        items = bundle.get("items", [])
        if not items:
            return None
        total = float(bundle.get("total_price", 0))
        currency = bundle.get("currency", "USD")
        user_id = bundle.get("user_id")

        order_result = client.table("orders").insert({
            "user_id": user_id,
            "bundle_id": bundle_id,
            "total_amount": total,
            "currency": currency,
            "status": "pending",
            "payment_status": "pending",
        }).execute()
        if not order_result.data:
            return None
        order_row = order_result.data[0]
        order_id = str(order_row["id"])

        legs_result = (
            client.table("bundle_legs")
            .select("id, leg_sequence, product_id, partner_id, price")
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
                product_names[str(p["id"])] = p.get("name", "Unknown")

        for leg in legs:
            product_id = leg.get("product_id")
            partner_id = leg.get("partner_id")
            price = float(leg.get("price", 0))
            item_name = product_names.get(str(product_id), "Unknown") if product_id else "Unknown"

            client.table("order_items").insert({
                "order_id": order_id,
                "product_id": product_id,
                "partner_id": partner_id,
                "item_name": item_name,
                "quantity": 1,
                "unit_price": price,
                "total_price": price,
            }).execute()

            client.table("order_legs").insert({
                "order_id": order_id,
                "bundle_leg_id": leg.get("id"),
                "partner_id": partner_id,
                "status": "pending",
            }).execute()

        line_items = [
            {"name": product_names.get(str(leg.get("product_id")), "Unknown"), "quantity": 1, "price": float(leg.get("price", 0)), "currency": currency}
            for leg in legs
        ]
        return {
            "id": order_id,
            "bundle_id": bundle_id,
            "subtotal": total,
            "total": total,
            "currency": currency,
            "line_items": line_items,
            "status": "pending",
            "payment_status": "pending",
        }
    except Exception:
        return None


async def remove_from_bundle(item_id: str) -> Optional[Dict[str, Any]]:
    """
    Remove a bundle leg (item) by id. Updates bundle total_price.
    item_id is the bundle_leg id from the bundle card.
    """
    client = get_supabase()
    if not client:
        return None
    try:
        leg_result = (
            client.table("bundle_legs")
            .select("id, bundle_id, price")
            .eq("id", item_id)
            .single()
            .execute()
        )
        if not leg_result.data:
            return None
        leg = leg_result.data
        bundle_id = leg.get("bundle_id")
        price = float(leg.get("price", 0))

        bundle_result = (
            client.table("bundles")
            .select("total_price, currency")
            .eq("id", bundle_id)
            .single()
            .execute()
        )
        if not bundle_result.data:
            return None
        total = float(bundle_result.data.get("total_price", 0)) - price
        total = max(0, total)

        client.table("bundle_legs").delete().eq("id", item_id).execute()
        client.table("bundles").update({"total_price": total}).eq("id", bundle_id).execute()

        return {
            "bundle_id": bundle_id,
            "item_removed_id": item_id,
            "total_price": total,
            "currency": bundle_result.data.get("currency", "USD"),
        }
    except Exception:
        return None
