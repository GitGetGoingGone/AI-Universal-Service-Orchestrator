"""Supabase DB for Hybrid Response Logic (Module 13)."""

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


def check_connection() -> bool:
    client = get_supabase()
    if not client:
        return False
    try:
        result = client.table("response_classifications").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


# Classification keywords for rule-based routing (no mock; deterministic)
ROUTINE_KEYWORDS = frozenset({
    "status", "track", "when", "where", "time", "delivery", "eta", "order number",
    "confirm", "quantity", "price", "total", "address", "phone", "email",
})
HUMAN_KEYWORDS = frozenset({
    "dispute", "wrong", "damage", "broken", "missing", "refund", "cancel", "complaint",
    "never received", "not what", "broken", "damaged", "fraud", "manager", "human",
    "speak to", "talk to", "representative", "escalate", "frustrated", "angry",
    "unacceptable", "terrible", "worst", "physical damage", "arrived broken",
})


def classify_message(content: str) -> str:
    """
    Classify message as routine, complex, dispute, or physical_damage.
    Returns classification and implied route: routine -> AI, others -> human.
    """
    text = (content or "").lower().strip()
    if not text:
        return "routine"

    words = set(text.replace(".", " ").replace(",", " ").split())
    if words & HUMAN_KEYWORDS:
        if any(k in text for k in ("damage", "broken", "arrived broken", "physical")):
            return "physical_damage"
        if any(k in text for k in ("dispute", "refund", "wrong charge", "fraud")):
            return "dispute"
        return "complex"
    if words & ROUTINE_KEYWORDS or len(text) < 100:
        return "routine"
    return "complex"


def create_classification_and_route(
    conversation_ref: str,
    message_content: str,
) -> Dict[str, Any]:
    """
    Classify message, log to response_classifications, create support_escalation if route=human.
    Returns { classification, route, support_escalation_id?, id }.
    """
    client = get_supabase()
    if not client:
        return {"classification": "complex", "route": "human", "support_escalation_id": None}

    classification = classify_message(message_content)
    route = "human" if classification in ("complex", "dispute", "physical_damage") else "ai"

    support_escalation_id = None
    if route == "human":
        r = client.table("support_escalations").insert({
            "conversation_ref": conversation_ref,
            "classification": classification,
            "status": "pending",
        }).select("id").execute()
        if r.data:
            support_escalation_id = str(r.data[0]["id"])

    r2 = client.table("response_classifications").insert({
        "conversation_ref": conversation_ref,
        "message_content": (message_content or "")[:5000],
        "classification": classification,
        "route": route,
        "support_escalation_id": support_escalation_id,
    }).select("id, classification, route, support_escalation_id").execute()

    row = r2.data[0] if r2.data else {}
    return {
        "id": str(row.get("id", "")),
        "classification": classification,
        "route": route,
        "support_escalation_id": str(row["support_escalation_id"]) if row.get("support_escalation_id") else None,
    }


def list_support_escalations(status: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return []
    q = client.table("support_escalations").select("*").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    r = q.execute()
    return r.data or []


def get_support_escalation(escalation_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    r = client.table("support_escalations").select("*").eq("id", escalation_id).execute()
    return r.data[0] if r.data else None


def assign_escalation(escalation_id: str, assigned_to: str) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if not client:
        return None
    r = client.table("support_escalations").update({"assigned_to": assigned_to, "status": "assigned"}).eq("id", escalation_id).select().execute()
    return r.data[0] if r.data else None


def resolve_escalation(escalation_id: str, resolution_notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
    from datetime import datetime, timezone
    client = get_supabase()
    if not client:
        return None
    now = datetime.now(timezone.utc).isoformat()
    upd = {"status": "resolved", "resolved_at": now}
    if resolution_notes is not None:
        upd["resolution_notes"] = resolution_notes
    r = client.table("support_escalations").update(upd).eq("id", escalation_id).select().execute()
    return r.data[0] if r.data else None
