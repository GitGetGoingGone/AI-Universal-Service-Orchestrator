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
            .select(
                "id, name, description, price, currency, capabilities, metadata, partner_id, "
                "url, brand, image_url, is_eligible_search, is_eligible_checkout, target_countries, availability"
            )
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
            .select(
                "id, name, description, price, currency, capabilities, metadata, partner_id, "
                "url, brand, image_url, is_eligible_search, is_eligible_checkout, target_countries, availability"
            )
            .eq("id", product_id)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def get_partner_by_id(partner_id: str) -> Optional[Dict[str, Any]]:
    """Get partner by ID with seller attribution and last_acp_push_at."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partners")
            .select(
                "id, business_name, seller_name, seller_url, return_policy_url, "
                "privacy_policy_url, terms_url, store_country, target_countries, last_acp_push_at"
            )
            .eq("id", partner_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def update_partner_last_acp_push(partner_id: str) -> bool:
    """Set last_acp_push_at to now for 15-minute throttle."""
    client = get_supabase()
    if not client:
        return False
    try:
        from datetime import datetime, timezone
        client.table("partners").update({
            "last_acp_push_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", partner_id).execute()
        return True
    except Exception:
        return False


async def update_products_last_acp_push(product_ids: List[str], success: bool) -> bool:
    """Set last_acp_push_at and last_acp_push_success for given products (for portal status)."""
    if not product_ids:
        return True
    client = get_supabase()
    if not client:
        return False
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        for pid in product_ids:
            client.table("products").update({
                "last_acp_push_at": now,
                "last_acp_push_success": success,
                "updated_at": now,
            }).eq("id", pid).execute()
        return True
    except Exception:
        return False


async def get_products_for_acp_export(
    partner_id: Optional[str] = None,
    product_id: Optional[str] = None,
    product_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Get products with partner seller fields joined for ACP feed building.
    Returns list of product dicts each with partner seller_* merged (seller_name, seller_url, etc.).
    """
    client = get_supabase()
    if not client:
        return []
    try:
        q = (
            client.table("products")
            .select(
                "id, name, description, price, currency, capabilities, metadata, partner_id, "
                "url, brand, image_url, is_eligible_search, is_eligible_checkout, target_countries, availability"
            )
            .is_("deleted_at", "null")
        )
        if partner_id:
            q = q.eq("partner_id", partner_id)
        if product_id:
            q = q.eq("id", product_id)
        elif product_ids:
            q = q.in_("id", product_ids)
        result = q.execute()
        products = result.data or []
        if not products:
            return []
        partner_ids = list({str(p["partner_id"]) for p in products if p.get("partner_id")})
        partners_map = {}
        for pid in partner_ids:
            partner = await get_partner_by_id(pid)
            if partner:
                partners_map[pid] = partner
        out = []
        for p in products:
            row = dict(p)
            pid = str(p.get("partner_id", "")) if p.get("partner_id") else ""
            partner = partners_map.get(pid) if pid else None
            if partner:
                row["seller_name"] = partner.get("seller_name") or partner.get("business_name")
                row["seller_url"] = partner.get("seller_url")
                row["return_policy"] = partner.get("return_policy_url")
                row["seller_privacy_policy"] = partner.get("privacy_policy_url")
                row["seller_tos"] = partner.get("terms_url")
                row["store_country"] = partner.get("store_country")
                if partner.get("target_countries") is not None and "target_countries" not in row or row.get("target_countries") is None:
                    row["target_countries"] = partner.get("target_countries")
            out.append(row)
        return out
    except Exception:
        return []


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


async def create_bundle_from_ucp_items(
    line_items: List[Dict[str, Any]],
    currency: str = "USD",
) -> Optional[str]:
    """
    Create a bundle from UCP line items. Each item: {item: {id: product_id}, quantity: int}.
    Returns bundle_id or None.
    """
    client = get_supabase()
    if not client or not line_items:
        return None
    try:
        bundle_result = client.table("bundles").insert({
            "bundle_name": "UCP Checkout",
            "total_price": 0,
            "currency": currency,
            "status": "draft",
        }).execute()
        if not bundle_result.data:
            return None
        bundle_id = str(bundle_result.data[0]["id"])
        total = 0.0
        seq = 1
        for li in line_items:
            item = li.get("item") or {}
            product_id = str(item.get("id", ""))
            qty = int(li.get("quantity", 1))
            if not product_id or qty < 1:
                continue
            product = await get_product_by_id(product_id)
            if not product:
                continue
            price = float(product.get("price", 0))
            partner_id = product.get("partner_id")
            for _ in range(qty):
                client.table("bundle_legs").insert({
                    "bundle_id": bundle_id,
                    "leg_sequence": seq,
                    "product_id": product_id,
                    "partner_id": partner_id,
                    "leg_type": "product",
                    "price": price,
                }).execute()
                total += price
                seq += 1
        client.table("bundles").update({"total_price": total}).eq("id", bundle_id).execute()
        return bundle_id
    except Exception:
        return None


async def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Get order with line items for UCP checkout."""
    client = get_supabase()
    if not client:
        return None
    try:
        order_result = (
            client.table("orders")
            .select("id, bundle_id, user_id, total_amount, currency, status, payment_status, created_at")
            .eq("id", order_id)
            .single()
            .execute()
        )
        if not order_result.data:
            return None
        order = dict(order_result.data)
        items_result = (
            client.table("order_items")
            .select("id, product_id, partner_id, item_name, quantity, unit_price, total_price")
            .eq("order_id", order_id)
            .execute()
        )
        order["items"] = items_result.data or []
        return order
    except Exception:
        return None


async def update_order_status(order_id: str, status: str, payment_status: Optional[str] = None) -> bool:
    """Update order status (and optionally payment_status)."""
    client = get_supabase()
    if not client:
        return False
    try:
        updates = {"status": status}
        if payment_status is not None:
            updates["payment_status"] = payment_status
        client.table("orders").update(updates).eq("id", order_id).execute()
        return True
    except Exception:
        return False


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


# --- Module 3: AI-First Discoverability ---


async def get_agent_action_models() -> List[Dict[str, Any]]:
    """Get active action models for AI agents."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("agent_action_models")
            .select(
                "action_name, method, endpoint, requires_auth, requires_approval_if_over, "
                "rate_limit_per_hour, allowed_parameters, restricted_parameters, "
                "allowed_modifications, restricted_modifications"
            )
            .eq("is_active", True)
            .order("action_name")
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def get_platform_manifest_config() -> Optional[Dict[str, Any]]:
    """Get active platform manifest config."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("platform_manifest_config")
            .select("*")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None
