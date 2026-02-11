"""Supabase DB for HubNegotiator & Bidding (Module 10)."""

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


async def check_connection() -> bool:
    client = get_supabase()
    if not client:
        return False
    try:
        result = client.table("rfps").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


def create_rfp(
    order_id: Optional[str] = None,
    bundle_id: Optional[str] = None,
    request_type: str = "assembly",
    title: str = "",
    description: Optional[str] = None,
    delivery_address: Optional[Dict] = None,
    deadline: str = "",
    compensation_cents: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    row = {
        "request_type": request_type,
        "title": title or "RFP",
        "description": description,
        "delivery_address": delivery_address,
        "deadline": deadline,
        "compensation_cents": compensation_cents,
        "status": "open",
    }
    if order_id:
        row["order_id"] = order_id
    if bundle_id:
        row["bundle_id"] = bundle_id
    r = client.table("rfps").insert(row).select().execute()
    return r.data[0] if r.data else None


def list_rfps(status: str = "open") -> List[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return []
    r = client.table("rfps").select("*").eq("status", status).order("deadline").execute()
    return r.data or []


def get_rfp(rfp_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    r = client.table("rfps").select("*").eq("id", rfp_id).execute()
    return r.data[0] if r.data else None


def get_bids_for_rfp(rfp_id: str) -> List[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return []
    r = client.table("bids").select("*").eq("rfp_id", rfp_id).order("amount_cents").execute()
    return r.data or []


def submit_bid(
    rfp_id: str,
    hub_partner_id: str,
    amount_cents: int,
    proposed_completion_at: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    rfp = get_rfp(rfp_id)
    if not rfp or rfp.get("status") != "open":
        return None
    row = {
        "rfp_id": rfp_id,
        "hub_partner_id": hub_partner_id,
        "amount_cents": amount_cents,
        "proposed_completion_at": proposed_completion_at,
        "status": "submitted",
    }
    try:
        r = client.table("bids").insert(row).select().execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def select_winning_bid(rfp_id: str, bid_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    rfp = get_rfp(rfp_id)
    if not rfp or rfp.get("status") != "open":
        return None
    bid = client.table("bids").select("*").eq("id", bid_id).eq("rfp_id", rfp_id).execute()
    if not bid.data:
        return None
    now = datetime.now(timezone.utc).isoformat()
    client.table("rfps").update({"status": "closed", "closed_at": now, "winning_bid_id": bid_id}).eq("id", rfp_id).execute()
    client.table("bids").update({"status": "won"}).eq("id", bid_id).execute()
    client.table("bids").update({"status": "lost"}).eq("rfp_id", rfp_id).neq("id", bid_id).execute()
    return get_rfp(rfp_id)


def get_hubs_with_capacity(available_from: str, available_until: str) -> List[str]:
    """Return list of partner_ids that have capacity overlapping the window."""
    client = get_supabase()
    if not client:
        return []
    r = (
        client.table("hub_capacity")
        .select("partner_id")
        .lte("available_from", available_until)
        .gte("available_until", available_from)
        .execute()
    )
    partner_ids = list({str(x["partner_id"]) for x in (r.data or [])})
    return partner_ids


def add_hub_capacity(
    partner_id: str,
    available_from: str,
    available_until: str,
    capacity_slots: int = 1,
) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "partner_id": partner_id,
        "capacity_slots": capacity_slots,
        "available_from": available_from,
        "available_until": available_until,
        "updated_at": now,
    }
    r = client.table("hub_capacity").insert(row).select().execute()
    return r.data[0] if r.data else None
