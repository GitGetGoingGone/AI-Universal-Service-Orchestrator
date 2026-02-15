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
