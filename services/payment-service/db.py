"""Supabase client for Payment Service."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


async def get_order_with_items(order_id: str) -> Optional[Dict[str, Any]]:
    """Get order with line items and partner splits."""
    client = get_supabase()
    if not client:
        return None
    try:
        order_result = (
            client.table("orders")
            .select("id, bundle_id, user_id, total_amount, currency, status, payment_status")
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


async def get_platform_config_sponsorship() -> Optional[Dict[str, Any]]:
    """Get sponsorship_pricing from platform_config."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("platform_config")
            .select("sponsorship_pricing")
            .limit(1)
            .single()
            .execute()
        )
        if result.data and result.data.get("sponsorship_pricing"):
            return result.data["sponsorship_pricing"]
        return {"product_price_per_day_cents": 1000, "sponsorship_enabled": True}
    except Exception:
        return {"product_price_per_day_cents": 1000, "sponsorship_enabled": True}


async def get_product_partner(product_id: str) -> Optional[Dict[str, Any]]:
    """Get product with partner_id. Returns None if not found."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("products")
            .select("id, partner_id")
            .eq("id", product_id)
            .is_("deleted_at", None)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def get_partner_stripe_account(partner_id: str) -> Optional[str]:
    """Get partner's Stripe Connect account ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partners")
            .select("stripe_account_id")
            .eq("id", partner_id)
            .single()
            .execute()
        )
        if result.data and result.data.get("stripe_account_id"):
            return result.data["stripe_account_id"]
        return None
    except Exception:
        return None


async def create_payment_record(
    order_id: str,
    amount: float,
    currency: str,
    stripe_payment_intent_id: str,
    status: str = "pending",
) -> Optional[Dict[str, Any]]:
    """Create payment record."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("payments").insert({
            "order_id": order_id,
            "payment_method": "stripe",
            "amount": amount,
            "currency": currency,
            "status": status,
            "stripe_payment_intent_id": stripe_payment_intent_id,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def update_payment_status(
    stripe_payment_intent_id: str,
    status: str,
    transaction_id: Optional[str] = None,
) -> bool:
    """Update payment status."""
    client = get_supabase()
    if not client:
        return False
    try:
        update = {"status": status}
        if status == "succeeded":
            update["captured_at"] = datetime.now(timezone.utc).isoformat()
        if transaction_id:
            update["transaction_id"] = transaction_id
        client.table("payments").update(update).eq(
            "stripe_payment_intent_id", stripe_payment_intent_id
        ).execute()
        return True
    except Exception:
        return False


async def update_order_payment_status(order_id: str, status: str) -> bool:
    """Update order payment_status."""
    client = get_supabase()
    if not client:
        return False
    try:
        update = {"payment_status": status}
        if status == "paid":
            update["paid_at"] = datetime.now(timezone.utc).isoformat()
        client.table("orders").update(update).eq("id", order_id).execute()
        return True
    except Exception:
        return False


async def create_product_sponsorship(
    product_id: str,
    partner_id: str,
    start_at: str,
    end_at: str,
    amount_cents: int,
    currency: str,
    stripe_payment_intent_id: str,
) -> Optional[Dict[str, Any]]:
    """Create product_sponsorships row after successful payment."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("product_sponsorships").insert({
            "product_id": product_id,
            "partner_id": partner_id,
            "start_at": start_at,
            "end_at": end_at,
            "amount_cents": amount_cents,
            "currency": currency,
            "status": "active",
            "stripe_payment_intent_id": stripe_payment_intent_id,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def create_payment_splits(
    payment_id: str,
    splits: List[Dict[str, Any]],
) -> bool:
    """Create payment split records for partners."""
    client = get_supabase()
    if not client:
        return False
    try:
        rows = [
            {
                "payment_id": payment_id,
                "recipient_type": s.get("recipient_type", "partner"),
                "recipient_id": s.get("recipient_id"),
                "amount": s["amount"],
                "currency": s.get("currency", "USD"),
                "split_type": s.get("split_type", "transfer"),
                "status": "pending",
            }
            for s in splits
        ]
        client.table("payment_splits").insert(rows).execute()
        return True
    except Exception:
        return False
