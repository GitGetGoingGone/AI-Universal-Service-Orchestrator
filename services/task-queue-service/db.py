"""Supabase DB for Multi-Vendor Task Queue (Module 11)."""

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
        result = client.table("vendor_tasks").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


def create_tasks_for_order(order_id: str) -> List[Dict[str, Any]]:
    """
    Create vendor_tasks from order_legs for an order.
    Order legs are ordered by bundle_leg.leg_sequence; one task per leg.
    Idempotent: returns existing tasks if order already has tasks.
    """
    client = get_supabase()
    if not client:
        return []

    existing = client.table("vendor_tasks").select("id, order_id, order_leg_id, partner_id, task_sequence, status").eq("order_id", order_id).execute()
    if existing.data:
        return existing.data

    legs = (
        client.table("order_legs")
        .select("id, order_id, partner_id, bundle_leg_id")
        .eq("order_id", order_id)
        .execute()
    )
    if not legs.data:
        return []

    # Get leg_sequence from bundle_legs
    leg_ids = [lg["bundle_leg_id"] for lg in legs.data if lg.get("bundle_leg_id")]
    if not leg_ids:
        # No bundle_leg_id: use creation order
        sorted_legs = sorted(legs.data, key=lambda x: x.get("id", ""))
    else:
        bl = (
            client.table("bundle_legs")
            .select("id, leg_sequence")
            .in_("id", leg_ids)
            .execute()
        )
        seq_by_id = {str(r["id"]): r["leg_sequence"] for r in (bl.data or [])}
        sorted_legs = sorted(
            legs.data,
            key=lambda x: (seq_by_id.get(str(x.get("bundle_leg_id")), 999), x.get("id", "")),
        )

    created = []
    for seq, leg in enumerate(sorted_legs, start=1):
        row = {
            "order_id": order_id,
            "order_leg_id": leg["id"],
            "partner_id": leg["partner_id"],
            "task_sequence": seq,
            "task_type": "fulfill",
            "status": "pending",
        }
        try:
            r = client.table("vendor_tasks").insert(row).select("id, order_id, order_leg_id, partner_id, task_sequence, status").execute()
            if r.data:
                created.append(r.data[0])
        except Exception:
            pass
    return created


def get_tasks_for_partner(partner_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List tasks for a partner. For pending tasks, only include those whose previous tasks
    in the same order are all completed (so partner sees "next available").
    """
    client = get_supabase()
    if not client:
        return []

    q = client.table("vendor_tasks").select("id, order_id, order_leg_id, partner_id, task_sequence, task_type, status, created_at, started_at, completed_at, metadata").eq("partner_id", partner_id)
    if status_filter:
        q = q.eq("status", status_filter)
    result = q.order("task_sequence").order("created_at").execute()
    tasks = result.data or []

    if status_filter and status_filter != "pending":
        return tasks

    # If no filter or pending: filter so partner only sees "available" pending (previous in order completed)
    out = []
    for t in tasks:
        if t["status"] in ("in_progress", "completed"):
            out.append(t)
            continue
        if t["status"] != "pending":
            continue
        # Check all tasks for same order with lower sequence are completed
        prev = (
            client.table("vendor_tasks")
            .select("id, status")
            .eq("order_id", t["order_id"])
            .lt("task_sequence", t["task_sequence"])
            .execute()
        )
        if prev.data and any(p.get("status") != "completed" for p in prev.data):
            continue
        out.append(t)
    return out


def get_task_by_id(task_id: str, partner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    q = client.table("vendor_tasks").select("*").eq("id", task_id)
    if partner_id:
        q = q.eq("partner_id", partner_id)
    r = q.execute()
    return r.data[0] if r.data else None


def start_task(task_id: str, partner_id: str) -> Optional[Dict[str, Any]]:
    from datetime import datetime, timezone
    client = get_supabase()
    if not client:
        return None
    task = get_task_by_id(task_id, partner_id)
    if not task or task.get("status") != "pending":
        return None
    now = datetime.now(timezone.utc).isoformat()
    r = (
        client.table("vendor_tasks")
        .update({"status": "in_progress", "started_at": now})
        .eq("id", task_id)
        .eq("partner_id", partner_id)
        .select()
        .execute()
    )
    if r.data:
        client.table("order_legs").update({"status": "in_progress"}).eq("id", task["order_leg_id"]).execute()
    return r.data[0] if r.data else None


def complete_task(task_id: str, partner_id: str, metadata: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
    from datetime import datetime, timezone
    client = get_supabase()
    if not client:
        return None
    task = get_task_by_id(task_id, partner_id)
    if not task or task.get("status") not in ("pending", "in_progress"):
        return None
    now = datetime.now(timezone.utc).isoformat()
    upd = {"status": "completed", "completed_at": now}
    if metadata is not None:
        upd["metadata"] = metadata
    r = (
        client.table("vendor_tasks")
        .update(upd)
        .eq("id", task_id)
        .eq("partner_id", partner_id)
        .select()
        .execute()
    )
    if r.data:
        client.table("order_legs").update({"status": "completed", "completed_at": now}).eq("id", task["order_leg_id"]).execute()
    return r.data[0] if r.data else None
