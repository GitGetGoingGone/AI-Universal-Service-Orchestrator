"""Supabase client for intent service (Module 4)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from config import settings

_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Get Supabase client."""
    global _client
    if _client is not None:
        return _client
    if not settings.supabase_configured:
        return None
    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def check_connection() -> bool:
    """Verify database connectivity."""
    client = get_supabase()
    if not client:
        return False
    try:
        result = client.table("intents").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


def create_intent(
    original_text: str,
    intent_type: str,
    entities: List[Dict[str, Any]],
    graph_data: Optional[Dict[str, Any]] = None,
    confidence_score: Optional[float] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create intent record and related entities.
    Returns the created intent with id.
    """
    client = get_supabase()
    if not client:
        raise RuntimeError("Supabase not configured")

    now = datetime.utcnow().isoformat()

    # Insert intent
    intent_row = {
        "original_text": original_text,
        "intent_type": intent_type,
        "status": "resolved",
        "resolved_at": now,
        "user_id": user_id,
    }
    intent_result = client.table("intents").insert(intent_row).execute()
    if not intent_result.data:
        raise RuntimeError("Failed to create intent")
    intent = intent_result.data[0]
    intent_id = intent["id"]

    # Insert intent_graphs if graph_data provided
    if graph_data:
        client.table("intent_graphs").insert({
            "intent_id": intent_id,
            "graph_data": graph_data,
            "entities": {"items": entities},
            "confidence_score": confidence_score,
        }).execute()

    # Insert intent_entities
    for e in entities:
        entity_type = e.get("type") or e.get("entity_type", "unknown")
        entity_value = e.get("value") or e.get("entity_value", "")
        confidence = e.get("confidence") or confidence_score
        client.table("intent_entities").insert({
            "intent_id": intent_id,
            "entity_type": entity_type,
            "entity_value": str(entity_value),
            "confidence": confidence,
        }).execute()

    return intent
