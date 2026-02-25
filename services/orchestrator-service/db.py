"""Supabase client for orchestrator (account_links, users, id_masking_map)."""

import uuid as uuid_module
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from supabase import create_client, Client

from config import settings

_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Get Supabase client. Returns None if not configured."""
    global _client
    if _client is not None:
        return _client
    if not _supabase_configured():
        return None
    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def _supabase_configured() -> bool:
    return bool(getattr(settings, "supabase_url", None) and getattr(settings, "supabase_key", None))


def store_masked_id(
    agent_slug: str,
    internal_product_id: str,
    partner_id: Optional[str] = None,
    source: str = "rpc",
) -> Optional[str]:
    """
    Store a masked id mapping for Gateway ID masking (uso_{agent_slug}_{short_id}).
    Used when merging broadcast discovery results so clients only see USO-owned ids.
    Returns masked_id or None if DB unavailable. TTL from settings.id_masking_ttl_hours.
    """
    client = get_supabase()
    if not client:
        return None
    short_uid = str(uuid_module.uuid4()).replace("-", "")[:16]
    masked_id = f"uso_{agent_slug}_{short_uid}"
    ttl_hours = getattr(settings, "id_masking_ttl_hours", 24)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
    try:
        client.table("id_masking_map").insert({
            "masked_id": masked_id,
            "internal_product_id": str(internal_product_id),
            "partner_id": str(partner_id) if partner_id else None,
            "source": source,
            "agent_slug": agent_slug,
            "expires_at": expires_at,
        }).execute()
        return masked_id
    except Exception:
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by UUID."""
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("users").select("*").eq("id", user_id).limit(1).execute()
        row = r.data[0] if r.data else None
        return cast(Optional[Dict[str, Any]], row)
    except Exception:
        return None


def get_user_by_clerk_id(clerk_user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by Clerk user ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("users").select("*").eq("clerk_user_id", clerk_user_id).limit(1).execute()
        row = r.data[0] if r.data else None
        return cast(Optional[Dict[str, Any]], row)
    except Exception:
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("users").select("*").eq("email", email).limit(1).execute()
        row = r.data[0] if r.data else None
        return cast(Optional[Dict[str, Any]], row)
    except Exception:
        return None


def upsert_user(
    *,
    clerk_user_id: Optional[str] = None,
    email: Optional[str] = None,
    display_name: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Find or create user. If user_id given, update that user. Else find by clerk_user_id or email, or create.
    """
    client = get_supabase()
    if not client:
        return None
    try:
        if user_id:
            updates = {}
            if clerk_user_id is not None:
                updates["clerk_user_id"] = clerk_user_id
            if email is not None:
                updates["email"] = email
            if display_name is not None:
                updates["display_name"] = display_name
            if updates:
                client.table("users").update(updates).eq("id", user_id).execute()
            r = client.table("users").select("*").eq("id", user_id).limit(1).execute()
            row = r.data[0] if r.data else None
            return cast(Optional[Dict[str, Any]], row)
        existing = None
        if clerk_user_id:
            existing = get_user_by_clerk_id(clerk_user_id)
        if not existing and email:
            existing = get_user_by_email(email)
        if existing:
            existing = cast(Dict[str, Any], existing)
            updates = {}
            if clerk_user_id and not existing.get("clerk_user_id"):
                updates["clerk_user_id"] = clerk_user_id
            if updates:
                client.table("users").update(updates).eq("id", existing["id"]).execute()
                r = client.table("users").select("*").eq("id", existing["id"]).limit(1).execute()
                row = r.data[0] if r.data else existing
                return cast(Optional[Dict[str, Any]], row)
            return existing
        # Create new user
        import uuid
        row = {
            "id": str(uuid.uuid4()),
            "email": email,
            "display_name": display_name or email,
            "clerk_user_id": clerk_user_id,
        }
        client.table("users").insert(row).execute()
        return row
    except Exception:
        return None


def get_account_links_by_user(user_id: str) -> List[Dict[str, Any]]:
    """Get all active account links for a user."""
    client = get_supabase()
    if not client:
        return []
    try:
        r = (
            client.table("account_links")
            .select("id, platform, platform_user_id, created_at")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        return cast(List[Dict[str, Any]], r.data or [])
    except Exception:
        return []


def get_account_link(user_id: str, platform: str, platform_user_id: str) -> Optional[Dict[str, Any]]:
    """Get one account link."""
    client = get_supabase()
    if not client:
        return None
    try:
        r = (
            client.table("account_links")
            .select("*")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .eq("platform_user_id", platform_user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        row = r.data[0] if r.data else None
        return cast(Optional[Dict[str, Any]], row)
    except Exception:
        return None


def upsert_account_link(
    user_id: str,
    platform: str,
    platform_user_id: str,
    *,
    oauth_token_hash: Optional[str] = None,
    permissions: Optional[Dict[str, Any]] = None,
    expires_at: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create or update account link. Uses UNIQUE(user_id, platform, platform_user_id)."""
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "user_id": user_id,
            "platform": platform,
            "platform_user_id": platform_user_id,
            "is_active": True,
        }
        if oauth_token_hash is not None:
            row["oauth_token_hash"] = oauth_token_hash
        if permissions is not None:
            row["permissions"] = permissions
        if expires_at is not None:
            row["expires_at"] = expires_at
        r = client.table("account_links").upsert(row, on_conflict="user_id,platform,platform_user_id").execute()
        out = r.data[0] if r.data else None
        return cast(Optional[Dict[str, Any]], out)
    except Exception:
        return None


async def get_adaptive_cards_setting(
    partner_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    """
    Resolve adaptive_cards_enabled: platform default, partner override, user override.
    Precedence: user > partner > platform. Returns True if adaptive cards should be shown.
    """
    client = get_supabase()
    if not client:
        return True  # Default when DB not configured

    try:
        # 1. Platform default
        platform_row = client.table("platform_config").select("adaptive_cards_enabled").limit(1).execute()
        use_cards = True
        if platform_row.data and platform_row.data[0] is not None:
            p0 = platform_row.data[0]
            val = p0.get("adaptive_cards_enabled") if isinstance(p0, dict) else None
            if val is not None:
                use_cards = bool(val)

        # 2. Partner override
        if partner_id:
            partner_row = (
                client.table("partners")
                .select("adaptive_cards_enabled")
                .eq("id", partner_id)
                .limit(1)
                .execute()
            )
            if partner_row.data and partner_row.data[0] is not None:
                p0 = partner_row.data[0]
                val = p0.get("adaptive_cards_enabled") if isinstance(p0, dict) else None
                if val is not None:
                    use_cards = bool(val)

        # 3. User override (users.metadata->>'adaptive_cards_enabled')
        if user_id:
            user_row = (
                client.table("users")
                .select("metadata")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            if user_row.data and user_row.data[0]:
                u0 = user_row.data[0]
                meta = u0.get("metadata") or {} if isinstance(u0, dict) else {}
                if isinstance(meta, dict) and "adaptive_cards_enabled" in meta:
                    use_cards = bool(meta["adaptive_cards_enabled"])

        return use_cards
    except Exception:
        return True


def get_user_id_by_platform_user(platform: str, platform_user_id: str) -> Optional[str]:
    """Resolve our user_id from a linked platform identity (e.g. for chat thread mapping)."""
    client = get_supabase()
    if not client:
        return None
    try:
        r = (
            client.table("account_links")
            .select("user_id")
            .eq("platform", platform)
            .eq("platform_user_id", platform_user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if r.data and r.data[0]:
            d = r.data[0]
            return str(d.get("user_id")) if isinstance(d, dict) else None
        return None
    except Exception:
        return None


def get_admin_orchestration_settings() -> Optional[Dict[str, Any]]:
    """Get admin orchestration settings (global_tone, model_temperature, autonomy_level, discovery_timeout_ms)."""
    client = get_supabase()
    if not client:
        return None
    try:
        r = (
            client.table("admin_orchestration_settings")
            .select("*")
            .limit(1)
            .execute()
        )
        row = r.data[0] if r.data else None
        if row and isinstance(row, dict):
            row.setdefault("planner_always_decides", False)
            row.setdefault("opening_instructions", None)
            row.setdefault("narrowing_instructions", None)
            row.setdefault("default_fulfillment_fields", None)
            row.setdefault("default_fulfillment_field_labels", None)
        return cast(Optional[Dict[str, Any]], row) if row and isinstance(row, dict) else None
    except Exception:
        return None


def get_thread_refinement_context(thread_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Load refinement context (proposed_plan, search_queries, fulfillment_context) for a thread."""
    if not thread_id:
        return None
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("chat_threads").select("refinement_context").eq("id", thread_id).limit(1).execute()
        row = r.data[0] if r.data else None
        row_dict = row if isinstance(row, dict) else {}
        ctx = row_dict.get("refinement_context")
        if isinstance(ctx, dict) and (
            ctx.get("proposed_plan") or ctx.get("search_queries") or ctx.get("fulfillment_context")
        ):
            return ctx
        if isinstance(ctx, dict):
            return ctx
        return None
    except Exception:
        return None


def set_thread_refinement_context(
    thread_id: Optional[str],
    proposed_plan: Optional[List[str]] = None,
    search_queries: Optional[List[str]] = None,
    fulfillment_context: Optional[Dict[str, str]] = None,
) -> None:
    """Persist refinement context for a thread. Merges with existing; None means do not change that key."""
    if not thread_id:
        return
    client = get_supabase()
    if not client:
        return
    try:
        from datetime import datetime, timezone
        # Load existing so we merge rather than overwrite
        r = client.table("chat_threads").select("refinement_context").eq("id", thread_id).limit(1).execute()
        existing = {}
        if r.data and isinstance(r.data[0], dict) and isinstance(r.data[0].get("refinement_context"), dict):
            existing = dict(r.data[0]["refinement_context"])
        if proposed_plan is not None:
            existing["proposed_plan"] = proposed_plan
        if search_queries is not None:
            existing["search_queries"] = search_queries
        if fulfillment_context is not None:
            existing["fulfillment_context"] = {k: v for k, v in fulfillment_context.items() if v}
        payload: Dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "refinement_context": existing if existing else None,
        }
        client.table("chat_threads").update(payload).eq("id", thread_id).execute()
    except Exception:
        pass


def log_orchestration_trace(
    trace_type: str,
    *,
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    query: Optional[str] = None,
    experience_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Log OrchestrationTrace for product discovery or bundle creation. Returns trace id or None."""
    if trace_type not in ("product_discovery", "bundle_created"):
        return None
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "trace_type": trace_type,
            "metadata": metadata or {},
        }
        if thread_id:
            row["thread_id"] = thread_id
        if user_id:
            row["user_id"] = user_id
        if query:
            row["query"] = query
        if experience_name:
            row["experience_name"] = experience_name
        r = client.table("orchestration_traces").insert(row).execute()
        if r.data and len(r.data) > 0:
            first = r.data[0]
            return str(first.get("id", "")) if isinstance(first, dict) else None
        return None
    except Exception:
        return None


def get_partner_representation_rules() -> Dict[str, Dict[str, Any]]:
    """Get partner_id -> {admin_weight, preferred_protocol} for PartnerBalancer."""
    client = get_supabase()
    if not client:
        return {}
    try:
        r = (
            client.table("partner_representation_rules")
            .select("partner_id, admin_weight, preferred_protocol")
            .execute()
        )
        out: Dict[str, Dict[str, Any]] = {}
        for raw in (r.data or []):
            row = cast(Dict[str, Any], raw) if isinstance(raw, dict) else {}
            pid = str(row.get("partner_id", ""))
            if pid:
                out[pid] = {
                    "admin_weight": float(row.get("admin_weight", 1.0)),
                    "preferred_protocol": str(row.get("preferred_protocol", "DB")).upper(),
                }
        return out
    except Exception:
        return {}
