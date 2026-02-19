"""Supabase client for orchestrator (account_links, users). Used by Link Account API."""

from typing import Any, Dict, List, Optional

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


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by UUID."""
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("users").select("*").eq("id", user_id).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def get_user_by_clerk_id(clerk_user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by Clerk user ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("users").select("*").eq("clerk_user_id", clerk_user_id).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    client = get_supabase()
    if not client:
        return None
    try:
        r = client.table("users").select("*").eq("email", email).limit(1).execute()
        return r.data[0] if r.data else None
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
            return r.data[0] if r.data else None
        existing = None
        if clerk_user_id:
            existing = get_user_by_clerk_id(clerk_user_id)
        if not existing and email:
            existing = get_user_by_email(email)
        if existing:
            updates = {}
            if clerk_user_id and not existing.get("clerk_user_id"):
                updates["clerk_user_id"] = clerk_user_id
            if updates:
                client.table("users").update(updates).eq("id", existing["id"]).execute()
                r = client.table("users").select("*").eq("id", existing["id"]).limit(1).execute()
                return r.data[0] if r.data else existing
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
        return r.data or []
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
        return r.data[0] if r.data else None
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
        return r.data[0] if r.data else None
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
            val = platform_row.data[0].get("adaptive_cards_enabled")
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
                val = partner_row.data[0].get("adaptive_cards_enabled")
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
                meta = user_row.data[0].get("metadata") or {}
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
            return r.data[0].get("user_id")
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
            .select("global_tone, model_temperature, autonomy_level, discovery_timeout_ms, ucp_prioritized")
            .limit(1)
            .execute()
        )
        row = r.data[0] if r.data else None
        return dict(row) if row else None
    except Exception:
        return None


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
            return str(r.data[0].get("id", ""))
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
        out = {}
        for row in (r.data or []):
            pid = str(row.get("partner_id", ""))
            if pid:
                out[pid] = {
                    "admin_weight": float(row.get("admin_weight", 1.0)),
                    "preferred_protocol": str(row.get("preferred_protocol", "DB")).upper(),
                }
        return out
    except Exception:
        return {}
