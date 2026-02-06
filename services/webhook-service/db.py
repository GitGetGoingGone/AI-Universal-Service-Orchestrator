"""Supabase client for webhook service."""

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


async def check_connection() -> bool:
    """Verify database connectivity."""
    client = get_supabase()
    if not client:
        return False
    try:
        result = client.table("webhook_deliveries").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


def log_webhook_delivery(
    platform: str,
    thread_id: str,
    payload: Dict[str, Any],
    status: str = "pending",
    failure_reason: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Log webhook delivery attempt to webhook_deliveries table."""
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "platform": platform,
            "thread_id": thread_id,
            "payload": payload,
            "status": status,
            "failure_reason": failure_reason,
        }
        result = client.table("webhook_deliveries").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def update_webhook_delivery(
    delivery_id: str,
    status: str,
    failure_reason: Optional[str] = None,
) -> bool:
    """Update webhook delivery status."""
    client = get_supabase()
    if not client:
        return False
    try:
        updates = {"status": status}
        if failure_reason:
            updates["failure_reason"] = failure_reason
        if status == "delivered":
            from datetime import datetime
            updates["delivered_at"] = datetime.utcnow().isoformat()
        client.table("webhook_deliveries").update(updates).eq("id", delivery_id).execute()
        return True
    except Exception:
        return False


def get_chat_thread_mapping(platform: str, thread_id: str) -> Optional[Dict[str, Any]]:
    """Get chat thread mapping for user."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("chat_thread_mappings")
            .select("*")
            .eq("platform", platform)
            .eq("thread_id", thread_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


def upsert_chat_thread_mapping(
    platform: str,
    thread_id: str,
    user_id: Optional[str] = None,
    platform_user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Register or update chat thread mapping. Used when ChatGPT/Gemini call chat with thread_id.
    Enables webhook push to the same thread later (e.g. from Durable Status Narrator).
    """
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "platform": platform,
            "thread_id": thread_id,
            "is_active": True,
        }
        if user_id:
            row["user_id"] = user_id
        if platform_user_id:
            row["platform_user_id"] = platform_user_id
        result = (
            client.table("chat_thread_mappings")
            .upsert(row, on_conflict="platform,thread_id")
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None
