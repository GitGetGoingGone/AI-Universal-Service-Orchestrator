"""Supabase DB for Reverse Logistics (Module 17)."""

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


async def check_connection() -> bool:
    client = get_supabase()
    if not client:
        return False
    try:
        result = client.table("return_requests").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


def create_return_request(
    order_id: str,
    partner_id: str,
    reason: str,
    reason_detail: Optional[str] = None,
    order_leg_id: Optional[str] = None,
    requester_id: Optional[str] = None,
    photo_url: Optional[str] = None,
    items: Optional[List[Dict[str, Any]]] = None,
    refund_amount_cents: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("return_requests").insert({
            "order_id": order_id,
            "partner_id": partner_id,
            "reason": reason,
            "reason_detail": reason_detail,
            "order_leg_id": order_leg_id,
            "requester_id": requester_id,
            "photo_url": photo_url,
            "items": items or [],
            "refund_amount_cents": refund_amount_cents,
            "status": "pending",
        }).select().execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def list_return_requests(
    order_id: Optional[str] = None,
    partner_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return []
    try:
        q = client.table("return_requests").select("*").order("created_at", desc=True)
        if order_id:
            q = q.eq("order_id", order_id)
        if partner_id:
            q = q.eq("partner_id", partner_id)
        if status:
            q = q.eq("status", status)
        r = q.execute()
        return r.data or []
    except Exception:
        return []


def get_return_request(return_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("return_requests").select("*").eq("id", return_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def approve_return_request(return_id: str) -> Optional[Dict[str, Any]]:
    from datetime import datetime, timezone

    client = get_supabase()
    if not client:
        return None
    try:
        now = datetime.now(timezone.utc).isoformat()
        r = client.table("return_requests").update({"status": "approved", "approved_at": now}).eq("id", return_id).select().execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def reject_return_request(return_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("return_requests").update({"status": "rejected"}).eq("id", return_id).select().execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def create_refund(return_request_id: str, order_id: str, amount_cents: int, currency: str = "USD") -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("refunds").insert({
            "return_request_id": return_request_id,
            "order_id": order_id,
            "amount_cents": amount_cents,
            "currency": currency,
            "status": "completed",
        }).select().execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def create_restock_event(return_request_id: str, product_id: str, quantity: int) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("restock_events").insert({
            "return_request_id": return_request_id,
            "product_id": product_id,
            "quantity": quantity,
        }).select().execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def complete_return_request(return_id: str) -> Optional[Dict[str, Any]]:
    from datetime import datetime, timezone

    client = get_supabase()
    if not client:
        return None
    try:
        now = datetime.now(timezone.utc).isoformat()
        r = client.table("return_requests").update({"status": "completed", "completed_at": now}).eq("id", return_id).select().execute()
        return r.data[0] if r.data else None
    except Exception:
        return None
