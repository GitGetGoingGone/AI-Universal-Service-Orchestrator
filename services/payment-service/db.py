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
    experience_session_id: Optional[str] = None,
    payment_type: str = "initial",
) -> Optional[Dict[str, Any]]:
    """Create payment record. Supports experience_session_id and payment_type for supplemental charges."""
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "order_id": order_id,
            "payment_method": "stripe",
            "amount": amount,
            "currency": currency,
            "status": status,
            "stripe_payment_intent_id": stripe_payment_intent_id,
            "payment_type": payment_type,
        }
        if experience_session_id:
            row["experience_session_id"] = experience_session_id
        result = client.table("payments").insert(row).execute()
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


def get_partner_vendor_type(partner_id: str) -> str:
    """
    Resolve vendor_type for commitment provider selection.
    If partner in shopify_curated_partners -> shopify; else local.
    """
    client = get_supabase()
    if not client:
        return "local"
    try:
        result = (
            client.table("shopify_curated_partners")
            .select("id")
            .eq("partner_id", partner_id)
            .limit(1)
            .execute()
        )
        if result.data and len(result.data) > 0:
            return "shopify"
        return "local"
    except Exception:
        return "local"


async def get_bundle_for_precheck(bundle_id: str) -> Optional[Dict[str, Any]]:
    """
    Get bundle with legs grouped by partner for commitment precheck.
    Returns { legs_by_partner: { partner_id: [ { product_id, item_name, price, quantity } ] }, currency }.
    """
    client = get_supabase()
    if not client:
        return None
    try:
        bundle_r = (
            client.table("bundles")
            .select("id, currency")
            .eq("id", bundle_id)
            .single()
            .execute()
        )
        if not bundle_r.data:
            return None
        bundle = dict(bundle_r.data)
        legs_r = (
            client.table("bundle_legs")
            .select("id, product_id, partner_id, price")
            .eq("bundle_id", bundle_id)
            .order("leg_sequence")
            .execute()
        )
        legs = legs_r.data or []
        product_ids = [l.get("product_id") for l in legs if l.get("product_id")]
        names = {}
        if product_ids:
            prod_r = (
                client.table("products")
                .select("id, name")
                .in_("id", product_ids)
                .execute()
            )
            for p in prod_r.data or []:
                names[str(p.get("id", ""))] = p.get("name", "Item")
        legs_by_partner: Dict[str, List[Dict[str, Any]]] = {}
        for leg in legs:
            pid = str(leg.get("partner_id", ""))
            if not pid:
                pid = "unknown"
            if pid not in legs_by_partner:
                legs_by_partner[pid] = []
            legs_by_partner[pid].append({
                "product_id": leg.get("product_id"),
                "item_name": names.get(str(leg.get("product_id", "")), "Item"),
                "price": str(float(leg.get("price", 0))),
                "quantity": 1,
                "title": names.get(str(leg.get("product_id", "")), "Item"),
            })
        return {
            "bundle_id": bundle_id,
            "currency": bundle.get("currency", "USD"),
            "legs_by_partner": legs_by_partner,
        }
    except Exception:
        return None


async def get_experience_session_legs_by_thread(thread_id: str) -> List[Dict[str, Any]]:
    """Get experience_session_legs for thread (via experience_sessions)."""
    client = get_supabase()
    if not client:
        return []
    try:
        sess = (
            client.table("experience_sessions")
            .select("id")
            .eq("thread_id", thread_id)
            .limit(1)
            .execute()
        )
        if not sess.data or not sess.data[0]:
            return []
        session_id = sess.data[0].get("id")
        legs = (
            client.table("experience_session_legs")
            .select("id, partner_id, product_id")
            .eq("experience_session_id", session_id)
            .execute()
        )
        return legs.data or []
    except Exception:
        return []


async def update_experience_session_leg_external_order(
    leg_id: str,
    external_order_id: str,
    external_reservation_id: str,
    vendor_type: str,
) -> bool:
    """Update leg with external order id after commitment complete."""
    client = get_supabase()
    if not client:
        return False
    try:
        from datetime import datetime, timezone

        client.table("experience_session_legs").update({
            "external_order_id": external_order_id,
            "external_reservation_id": external_reservation_id,
            "vendor_type": vendor_type,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", leg_id).execute()
        return True
    except Exception:
        return False


async def transition_legs_to_in_customization(thread_id: str) -> int:
    """After payment: set experience_session_legs to in_customization when partner has available_to_customize."""
    client = get_supabase()
    if not client:
        return 0
    try:
        sess = (
            client.table("experience_sessions")
            .select("id")
            .eq("thread_id", thread_id)
            .limit(1)
            .execute()
        )
        if not sess.data or not sess.data[0]:
            return 0
        session_id = sess.data[0].get("id")
        legs = (
            client.table("experience_session_legs")
            .select("id, partner_id")
            .eq("experience_session_id", session_id)
            .eq("status", "ready")
            .execute()
        )
        if not legs.data:
            return 0
        partner_ids = list({str(l["partner_id"]) for l in legs.data if l.get("partner_id")})
        scp = (
            client.table("shopify_curated_partners")
            .select("partner_id, internal_agent_registry_id")
            .in_("partner_id", partner_ids)
            .execute()
        )
        reg_ids = [r.get("internal_agent_registry_id") for r in (scp.data or []) if r.get("internal_agent_registry_id")]
        customizable = set()
        if reg_ids:
            regs = (
                client.table("internal_agent_registry")
                .select("id")
                .in_("id", reg_ids)
                .eq("available_to_customize", True)
                .execute()
            )
            reg_set = {str(r["id"]) for r in (regs.data or [])}
            for r in scp.data or []:
                if str(r.get("internal_agent_registry_id", "")) in reg_set:
                    customizable.add(str(r.get("partner_id", "")))
        now = datetime.now(timezone.utc).isoformat()
        count = 0
        for leg in legs.data:
            if str(leg.get("partner_id", "")) in customizable:
                client.table("experience_session_legs").update({
                    "status": "in_customization",
                    "updated_at": now,
                }).eq("id", leg["id"]).execute()
                count += 1
        return count
    except Exception:
        return 0


async def update_order_leg_external_order(
    order_id: str,
    partner_id: str,
    external_order_id: str,
    external_reservation_id: str,
    vendor_type: str,
) -> bool:
    """Update order_leg(s) for partner with external order id."""
    client = get_supabase()
    if not client:
        return False
    try:
        legs = (
            client.table("order_legs")
            .select("id")
            .eq("order_id", order_id)
            .eq("partner_id", partner_id)
            .execute()
        )
        for leg in legs.data or []:
            client.table("order_legs").update({
                "external_order_id": external_order_id,
                "external_reservation_id": external_reservation_id,
                "vendor_type": vendor_type,
            }).eq("id", leg["id"]).execute()
        return True
    except Exception:
        return False


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
