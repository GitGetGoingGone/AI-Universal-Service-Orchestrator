"""Supabase DB for Virtual Proofing Engine (Module 8)."""

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
        result = client.table("proof_states").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


def _log_transition(proof_state_id: str, from_state: str, to_state: str, transitioned_by: Optional[str] = None, reason: Optional[str] = None) -> None:
    client = get_supabase()
    if not client:
        return
    try:
        client.table("proof_state_transitions").insert({
            "proof_state_id": proof_state_id,
            "from_state": from_state,
            "to_state": to_state,
            "transitioned_by": transitioned_by,
            "transition_reason": reason,
        }).execute()
    except Exception:
        pass


def create_proof_state(
    order_id: str,
    order_leg_id: Optional[str] = None,
    proof_type: str = "virtual_preview",
    prompt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("proof_states").insert({
            "order_id": order_id,
            "order_leg_id": order_leg_id,
            "proof_type": proof_type,
            "current_state": "pending",
            "prompt_used": prompt,
        }).select().execute()
        row = r.data[0] if r.data else None
        if row:
            _log_transition(str(row["id"]), None, "pending")
        return row
    except Exception:
        return None


def get_proof_state(proof_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("proof_states").select("*").eq("id", proof_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def list_proof_states(order_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return []
    try:
        q = client.table("proof_states").select("*").order("created_at", desc=True)
        if order_id:
            q = q.eq("order_id", order_id)
        if status:
            q = q.eq("current_state", status)
        r = q.execute()
        return r.data or []
    except Exception:
        return []


def set_proof_ready(proof_id: str, proof_image_url: str, submitted_by: Optional[str] = None) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        ps = get_proof_state(proof_id)
        if not ps or ps.get("current_state") not in ("pending", "in_progress"):
            return None
        now = datetime.now(timezone.utc).isoformat()
        r = client.table("proof_states").update({
            "current_state": "proof_ready",
            "proof_image_url": proof_image_url,
            "submitted_at": now,
            "submitted_by": submitted_by,
            "updated_at": now,
        }).eq("id", proof_id).select().execute()
        row = r.data[0] if r.data else None
        if row:
            _log_transition(proof_id, ps["current_state"], "proof_ready", submitted_by)
        return row
    except Exception:
        return None


def approve_proof(proof_id: str, approved_by: Optional[str] = None, method: str = "human", confidence: Optional[float] = None) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        ps = get_proof_state(proof_id)
        if not ps or ps.get("current_state") != "proof_ready":
            return None
        now = datetime.now(timezone.utc).isoformat()
        upd = {"current_state": "approved", "approved_at": now, "approved_by": approved_by, "approval_method": method, "updated_at": now}
        if confidence is not None:
            upd["approval_confidence"] = confidence
        r = client.table("proof_states").update(upd).eq("id", proof_id).select().execute()
        row = r.data[0] if r.data else None
        if row:
            _log_transition(proof_id, "proof_ready", "approved", approved_by)
        return row
    except Exception:
        return None


def reject_proof(proof_id: str, rejection_reason: Optional[str] = None, rejected_by: Optional[str] = None) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        ps = get_proof_state(proof_id)
        if not ps or ps.get("current_state") != "proof_ready":
            return None
        now = datetime.now(timezone.utc).isoformat()
        r = client.table("proof_states").update({
            "current_state": "rejected",
            "rejection_reason": rejection_reason,
            "approved_by": rejected_by,
            "updated_at": now,
        }).eq("id", proof_id).select().execute()
        row = r.data[0] if r.data else None
        if row:
            _log_transition(proof_id, "proof_ready", "rejected", rejected_by, rejection_reason)
        return row
    except Exception:
        return None


def set_in_progress(proof_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    try:
        ps = get_proof_state(proof_id)
        if not ps or ps.get("current_state") != "pending":
            return None
        now = datetime.now(timezone.utc).isoformat()
        r = client.table("proof_states").update({"current_state": "in_progress", "updated_at": now}).eq("id", proof_id).select().execute()
        row = r.data[0] if r.data else None
        if row:
            _log_transition(proof_id, "pending", "in_progress")
        return row
    except Exception:
        return None
