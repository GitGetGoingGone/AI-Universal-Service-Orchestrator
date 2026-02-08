"""Supabase client for Re-Sourcing Service - order and bundle updates."""

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


async def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Get order with bundle_id."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("orders")
            .select("id, bundle_id, total_amount, currency, user_id")
            .eq("id", order_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def get_order_leg(order_leg_id: str) -> Optional[Dict[str, Any]]:
    """Get order leg by ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("order_legs")
            .select("id, order_id, bundle_leg_id, partner_id, status")
            .eq("id", order_leg_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def cancel_order_leg(order_leg_id: str) -> bool:
    """Cancel order leg (status = 'cancelled')."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("order_legs").update({"status": "cancelled"}).eq("id", order_leg_id).execute()
        return True
    except Exception:
        return False


async def get_bundle_leg(bundle_leg_id: str) -> Optional[Dict[str, Any]]:
    """Get bundle leg by ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("bundle_legs")
            .select("id, bundle_id, leg_sequence, product_id, partner_id, price")
            .eq("id", bundle_leg_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def add_product_to_bundle(
    bundle_id: str,
    product_id: str,
    partner_id: Optional[str],
    price: float,
) -> Optional[Dict[str, Any]]:
    """Add a new bundle leg. Returns the new leg."""
    client = get_supabase()
    if not client:
        return None
    try:
        seq_result = (
            client.table("bundle_legs")
            .select("leg_sequence")
            .eq("bundle_id", bundle_id)
            .order("leg_sequence", desc=True)
            .limit(1)
            .execute()
        )
        next_seq = (seq_result.data[0]["leg_sequence"] + 1) if seq_result.data else 1

        leg_result = client.table("bundle_legs").insert({
            "bundle_id": bundle_id,
            "leg_sequence": next_seq,
            "product_id": product_id,
            "partner_id": partner_id,
            "leg_type": "product",
            "price": price,
        }).execute()
        if not leg_result.data:
            return None

        # Update bundle total
        bundle_result = (
            client.table("bundles")
            .select("total_price")
            .eq("id", bundle_id)
            .single()
            .execute()
        )
        if bundle_result.data:
            total = float(bundle_result.data.get("total_price", 0)) + price
            client.table("bundles").update({"total_price": total}).eq("id", bundle_id).execute()

        return leg_result.data[0]
    except Exception:
        return None


async def add_order_item_and_leg(
    order_id: str,
    product_id: str,
    partner_id: Optional[str],
    item_name: str,
    unit_price: float,
    bundle_leg_id: str,
) -> bool:
    """Add order_item and order_leg for the new product."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("order_items").insert({
            "order_id": order_id,
            "product_id": product_id,
            "partner_id": partner_id,
            "item_name": item_name,
            "quantity": 1,
            "unit_price": unit_price,
            "total_price": unit_price,
        }).execute()

        client.table("order_legs").insert({
            "order_id": order_id,
            "bundle_leg_id": bundle_leg_id,
            "partner_id": partner_id,
            "status": "pending",
        }).execute()

        # Update order total
        order_result = (
            client.table("orders")
            .select("total_amount")
            .eq("id", order_id)
            .single()
            .execute()
        )
        if order_result.data:
            total = float(order_result.data.get("total_amount", 0)) + unit_price
            client.table("orders").update({"total_amount": total}).eq("id", order_id).execute()

        return True
    except Exception:
        return False


async def create_autonomous_recovery(
    order_id: str,
    original_leg_id: str,
    change_request: Dict[str, Any],
    partner_rejection: Dict[str, Any],
    recovery_action: str,
    alternative_item_id: Optional[str] = None,
    alternative_vendor_id: Optional[str] = None,
    timeline_changed: bool = False,
    delay_minutes: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Create autonomous_recoveries record."""
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "order_id": order_id,
            "original_leg_id": original_leg_id,
            "change_request": change_request,
            "partner_rejection": partner_rejection,
            "recovery_action": recovery_action,
            "status": "completed",
        }
        if alternative_item_id:
            row["alternative_item_id"] = alternative_item_id
        if alternative_vendor_id:
            row["alternative_vendor_id"] = alternative_vendor_id
        if timeline_changed is not None:
            row["timeline_changed"] = timeline_changed
        if delay_minutes is not None:
            row["delay_minutes"] = delay_minutes

        result = client.table("autonomous_recoveries").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def create_escalation(negotiation_id: str, reason: str) -> bool:
    """Create escalation when no alternative found."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("escalations").insert({
            "negotiation_id": negotiation_id,
            "escalation_reason": reason,
            "severity": "medium",
            "status": "pending",
        }).execute()
        return True
    except Exception:
        return False
