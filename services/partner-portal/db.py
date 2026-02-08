"""Supabase database client for partner portal."""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from config import settings

_client: Optional[Client] = None
logger = logging.getLogger(__name__)


def get_supabase() -> Optional[Client]:
    """Get Supabase client."""
    global _client
    if _client is not None:
        return _client
    if not settings.supabase_configured:
        return None
    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


async def create_partner(
    business_name: str,
    contact_email: str,
    business_type: Optional[str] = None,
    contact_phone: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create a new partner. user_id omitted for MVP (no auth)."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("partners").insert({
            "business_name": business_name,
            "contact_email": contact_email,
            "business_type": business_type or "retail",
            "contact_phone": contact_phone,
            "verification_status": "pending",
            "is_active": True,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def get_partner_by_id(partner_id: str) -> Optional[Dict[str, Any]]:
    """Get partner by ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partners")
            .select("*")
            .eq("id", partner_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def list_partners(limit: int = 50) -> List[Dict[str, Any]]:
    """List all active partners."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("partners")
            .select("id, business_name, contact_email, business_type, is_active")
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def update_partner(partner_id: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """Update partner fields."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partners")
            .update(kwargs)
            .eq("id", partner_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def create_product(
    partner_id: str,
    name: str,
    price: float,
    description: Optional[str] = None,
    currency: str = "USD",
    capabilities: Optional[list] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    image_url: Optional[str] = None,
    category_id: Optional[str] = None,
    is_available: bool = True,
) -> Optional[Dict[str, Any]]:
    """Create a product for a partner."""
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "partner_id": partner_id,
            "name": name,
            "price": price,
            "currency": currency,
            "is_available": is_available,
        }
        if description:
            row["description"] = description
        if capabilities:
            row["capabilities"] = capabilities
        if price_min is not None:
            row["price_min"] = price_min
        if price_max is not None:
            row["price_max"] = price_max
        if image_url:
            row["image_url"] = image_url
        if category_id:
            row["category_id"] = category_id
        result = client.table("products").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def update_product(
    product_id: str,
    partner_id: str,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """Update a product. kwargs can include name, price, description, price_min, price_max, is_available, etc."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("products")
            .update({k: v for k, v in kwargs.items() if v is not None})
            .eq("id", product_id)
            .eq("partner_id", partner_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def soft_delete_product(product_id: str, partner_id: str) -> bool:
    """Soft delete a product by setting deleted_at."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("products").update({
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "is_available": False,
        }).eq("id", product_id).eq("partner_id", partner_id).execute()
        return True
    except Exception:
        return False


async def get_product_by_id(product_id: str, partner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a product by ID. Optionally verify partner_id."""
    client = get_supabase()
    if not client:
        return None
    try:
        q = client.table("products").select("*").eq("id", product_id).is_("deleted_at", "null")
        if partner_id:
            q = q.eq("partner_id", partner_id)
        result = q.single().execute()
        return result.data
    except Exception:
        return None


async def list_products(partner_id: str) -> List[Dict[str, Any]]:
    """List products for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("products")
            .select("id, name, description, price, currency, capabilities, price_min, price_max, is_available, image_url, category_id")
            .eq("partner_id", partner_id)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning("list_products error: %s", e)
        return []


async def verify_api_key(key: str) -> Optional[str]:
    """Verify API key and return partner_id if valid."""
    if not key or not key.startswith("pp_"):
        return None
    prefix = key[:12]
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partner_api_keys")
            .select("partner_id, key_hash")
            .eq("key_prefix", prefix)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        row = result.data[0]
        if row.get("key_hash") == key_hash:
            return str(row["partner_id"])
        return None
    except Exception as e:
        logger.warning("verify_api_key error: %s", e)
        return None


def _generate_api_key() -> tuple[str, str]:
    """Generate new API key. Returns (full_key, key_prefix)."""
    import secrets
    raw = secrets.token_hex(24)
    full_key = f"pp_{raw}"
    prefix = full_key[:12]
    return full_key, prefix


async def create_api_key(
    partner_id: str,
    name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create API key for partner. Returns dict with key, key_prefix, id."""
    full_key, prefix = _generate_api_key()
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("partner_api_keys").insert({
            "partner_id": partner_id,
            "key_hash": key_hash,
            "key_prefix": prefix,
            "name": name or "Default",
            "is_active": True,
        }).execute()
        if result.data:
            row = result.data[0]
            return {
                "id": str(row["id"]),
                "key": full_key,
                "key_prefix": prefix,
                "name": row.get("name"),
            }
    except Exception as e:
        logger.warning("create_api_key error: %s", e)
    return None


CHANNELS = ("api", "demo_chat", "whatsapp", "chatgpt", "gemini")


async def set_partner_channel(
    partner_id: str,
    channel: str,
    channel_identifier: str,
) -> Optional[Dict[str, Any]]:
    """
    Set partner's preferred channel for change requests.
    channel: api | demo_chat | whatsapp
    channel_identifier: webhook URL (api), "enabled" (demo_chat), phone number (whatsapp)
    """
    client = get_supabase()
    if not client:
        return None
    if channel not in CHANNELS:
        return None
    try:
        # Remove other channels for this partner (one primary channel)
        client.table("communication_preferences").delete().eq(
            "partner_id", partner_id
        ).execute()

        identifier = channel_identifier.strip() if channel_identifier else ("enabled" if channel == "demo_chat" else "")
        if channel == "api" and not identifier:
            return None
        if channel == "whatsapp" and not identifier:
            return None

        result = client.table("communication_preferences").insert({
            "partner_id": partner_id,
            "channel": channel,
            "channel_identifier": identifier or "enabled",
            "is_preferred": True,
            "is_active": True,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def get_partner_channel(partner_id: str) -> Optional[Dict[str, Any]]:
    """Get partner's preferred channel (channel, channel_identifier)."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("communication_preferences")
            .select("channel, channel_identifier")
            .eq("partner_id", partner_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception:
        return None


async def set_partner_webhook(partner_id: str, webhook_url: str) -> Optional[Dict[str, Any]]:
    """Legacy: Set partner webhook URL (channel=api)."""
    return await set_partner_channel(partner_id, "api", webhook_url)


async def get_partner_webhook(partner_id: str) -> Optional[str]:
    """Get partner webhook URL (if channel=api). Legacy compat."""
    prefs = await get_partner_channel(partner_id)
    if prefs and prefs.get("channel") == "api":
        return prefs.get("channel_identifier")
    return None


async def get_pending_negotiations(partner_id: str) -> list:
    """Get negotiations awaiting partner reply for demo chat."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("negotiations")
            .select("id, order_id, order_leg_id, negotiation_type, status, original_request, created_at")
            .eq("partner_id", partner_id)
            .eq("status", "awaiting_partner_reply")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


# --- Partner members ---
async def list_partner_members(partner_id: str) -> List[Dict[str, Any]]:
    """List team members for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("partner_members")
            .select("*")
            .eq("partner_id", partner_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def add_partner_member(
    partner_id: str,
    email: str,
    role: str = "member",
    display_name: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Add a team member (invite or record-only)."""
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "partner_id": partner_id,
            "email": email,
            "role": role,
            "display_name": display_name,
            "user_id": user_id,
        }
        result = client.table("partner_members").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def update_partner_member(
    member_id: str, partner_id: str, **kwargs: Any
) -> Optional[Dict[str, Any]]:
    """Update a team member."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partner_members")
            .update(kwargs)
            .eq("id", member_id)
            .eq("partner_id", partner_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def is_partner_admin(user_id: str, partner_id: str) -> bool:
    """Check if user is partner owner or admin."""
    client = get_supabase()
    if not client:
        return False
    try:
        result = (
            client.table("partner_members")
            .select("role")
            .eq("partner_id", partner_id)
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        if result.data:
            return result.data[0].get("role") in ("owner", "admin")
        return False
    except Exception:
        return False


async def is_platform_admin(user_id: str) -> bool:
    """Check if user is platform admin."""
    client = get_supabase()
    if not client:
        return False
    try:
        result = (
            client.table("platform_admins")
            .select("id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception:
        return False


async def is_partner_owner(user_id: str, partner_id: str) -> bool:
    """Check if user is partner owner."""
    client = get_supabase()
    if not client:
        return False
    try:
        result = (
            client.table("partner_members")
            .select("id")
            .eq("partner_id", partner_id)
            .eq("user_id", user_id)
            .eq("role", "owner")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception:
        return False


async def list_partner_admins(partner_id: str) -> List[Dict[str, Any]]:
    """List partner admins (owner and admin roles)."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("partner_members")
            .select("*")
            .eq("partner_id", partner_id)
            .in_("role", ["owner", "admin"])
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def add_platform_admin(user_id: str, scope: str = "all") -> Optional[Dict[str, Any]]:
    """Add platform admin."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("platform_admins").insert({
            "user_id": user_id,
            "scope": scope,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def list_platform_admins() -> List[Dict[str, Any]]:
    """List platform admins."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("platform_admins")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


# --- Partner schedules ---
async def get_partner_schedules(partner_id: str) -> List[Dict[str, Any]]:
    """Get business hours for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("partner_schedules")
            .select("*")
            .eq("partner_id", partner_id)
            .eq("is_active", True)
            .order("day_of_week")
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def replace_partner_schedules(
    partner_id: str, schedules: List[Dict[str, Any]]
) -> bool:
    """Replace partner's weekly schedule."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("partner_schedules").delete().eq("partner_id", partner_id).execute()
        if schedules:
            rows = [
                {
                    "partner_id": partner_id,
                    "day_of_week": s["day_of_week"],
                    "start_time": s["start_time"],
                    "end_time": s["end_time"],
                    "timezone": s.get("timezone", "UTC"),
                }
                for s in schedules
            ]
            client.table("partner_schedules").insert(rows).execute()
        return True
    except Exception:
        return False


# --- Product availability ---
async def list_product_availability(product_id: str) -> List[Dict[str, Any]]:
    """List availability slots for a product."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("product_availability")
            .select("*")
            .eq("product_id", product_id)
            .order("start_at")
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def add_product_availability(
    product_id: str,
    slot_type: str,
    start_at: str,
    end_at: str,
    capacity: int = 1,
    booking_mode: str = "auto_book",
    timezone: str = "UTC",
) -> Optional[Dict[str, Any]]:
    """Add availability slot."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("product_availability").insert({
            "product_id": product_id,
            "slot_type": slot_type,
            "start_at": start_at,
            "end_at": end_at,
            "capacity": capacity,
            "booking_mode": booking_mode,
            "timezone": timezone,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def update_product_availability(
    slot_id: str, **kwargs: Any
) -> Optional[Dict[str, Any]]:
    """Update availability slot."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("product_availability")
            .update(kwargs)
            .eq("id", slot_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def delete_product_availability(slot_id: str) -> bool:
    """Delete availability slot."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("product_availability").delete().eq("id", slot_id).execute()
        return True
    except Exception:
        return False


# --- Product assignments ---
async def list_product_assignments(product_id: str) -> List[Dict[str, Any]]:
    """List team members assigned to a product."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("product_assignments")
            .select("*, partner_members(*)")
            .eq("product_id", product_id)
            .execute()
        )
        return result.data or []
    except Exception:
        try:
            result = (
                client.table("product_assignments")
                .select("*")
                .eq("product_id", product_id)
                .execute()
            )
            return result.data or []
        except Exception:
            return []


async def add_product_assignment(
    product_id: str, partner_member_id: str, role: str = "handler"
) -> Optional[Dict[str, Any]]:
    """Assign team member to product."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("product_assignments").insert({
            "product_id": product_id,
            "partner_member_id": partner_member_id,
            "role": role,
        }).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def remove_product_assignment(product_id: str, partner_member_id: str) -> bool:
    """Remove team member from product."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("product_assignments").delete().eq(
            "product_id", product_id
        ).eq("partner_member_id", partner_member_id).execute()
        return True
    except Exception:
        return False


# --- Payouts ---
async def list_payouts(partner_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """List payouts for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("payouts")
            .select("*")
            .eq("partner_id", partner_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def list_commission_breaks(partner_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """List commission breakdown per order."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("commission_breaks")
            .select("*")
            .eq("partner_id", partner_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def get_earnings_summary(partner_id: str) -> Dict[str, Any]:
    """Earnings summary (gross, commission, net) from commission_breaks."""
    breaks = await list_commission_breaks(partner_id, limit=1000)
    gross = sum(b.get("gross_cents", 0) for b in breaks)
    commission = sum(b.get("commission_cents", 0) for b in breaks)
    net = sum(b.get("net_cents", 0) for b in breaks)
    return {
        "gross_cents": gross,
        "commission_cents": commission,
        "net_cents": net,
        "gross": round(gross / 100, 2),
        "commission": round(commission / 100, 2),
        "net": round(net / 100, 2),
    }


# --- Product categories ---
async def list_product_categories(partner_id: str) -> List[Dict[str, Any]]:
    """List product categories for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("product_categories")
            .select("*")
            .eq("partner_id", partner_id)
            .order("sort_order")
            .execute()
        )
        return result.data or []
    except Exception:
        return []


# --- Product inventory ---
async def get_product_inventory(product_id: str) -> Optional[Dict[str, Any]]:
    """Get inventory for a product."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("product_inventory")
            .select("*")
            .eq("product_id", product_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def upsert_product_inventory(
    product_id: str,
    quantity: int,
    low_stock_threshold: int = 5,
    auto_unlist_when_zero: bool = True,
) -> Optional[Dict[str, Any]]:
    """Create or update product inventory."""
    client = get_supabase()
    if not client:
        return None
    try:
        existing = await get_product_inventory(product_id)
        row = {
            "product_id": product_id,
            "quantity": quantity,
            "low_stock_threshold": low_stock_threshold,
            "auto_unlist_when_zero": auto_unlist_when_zero,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if existing:
            result = (
                client.table("product_inventory")
                .update(row)
                .eq("product_id", product_id)
                .execute()
            )
        else:
            result = client.table("product_inventory").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


# --- Promotions ---
async def list_partner_promotions(partner_id: str) -> List[Dict[str, Any]]:
    """List promotions for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("partner_promotions")
            .select("*")
            .eq("partner_id", partner_id)
            .order("start_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def add_partner_promotion(
    partner_id: str,
    name: str,
    promo_type: str,
    start_at: str,
    end_at: str,
    value: Optional[float] = None,
    product_ids: Optional[List[str]] = None,
    is_active: bool = True,
) -> Optional[Dict[str, Any]]:
    """Create promotion."""
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "partner_id": partner_id,
            "name": name,
            "promo_type": promo_type,
            "start_at": start_at,
            "end_at": end_at,
            "is_active": is_active,
        }
        if value is not None:
            row["value"] = value
        if product_ids:
            row["product_ids"] = product_ids
        result = client.table("partner_promotions").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


async def update_partner_promotion(
    promo_id: str, partner_id: str, **kwargs: Any
) -> Optional[Dict[str, Any]]:
    """Update promotion."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partner_promotions")
            .update(kwargs)
            .eq("id", promo_id)
            .eq("partner_id", partner_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def delete_partner_promotion(promo_id: str, partner_id: str) -> bool:
    """Delete promotion."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("partner_promotions").delete().eq("id", promo_id).eq(
            "partner_id", partner_id
        ).execute()
        return True
    except Exception:
        return False


# --- Partner venues ---
async def list_partner_venues(partner_id: str) -> List[Dict[str, Any]]:
    """List venues for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("partner_venues")
            .select("*")
            .eq("partner_id", partner_id)
            .eq("is_active", True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


# --- Partner ratings ---
async def get_partner_rating(partner_id: str) -> Optional[Dict[str, Any]]:
    """Get aggregate rating for a partner."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partner_ratings")
            .select("*")
            .eq("partner_id", partner_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def list_partner_reviews(partner_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """List reviews for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("order_reviews")
            .select("*")
            .eq("partner_id", partner_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def update_order_review_response(
    review_id: str, partner_id: str, partner_response: str
) -> Optional[Dict[str, Any]]:
    """Add partner response to review."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("order_reviews")
            .update({
                "partner_response": partner_response,
                "responded_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", review_id)
            .eq("partner_id", partner_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


# --- Notifications ---
async def list_partner_notifications(
    partner_id: str, limit: int = 50, unread_only: bool = False
) -> List[Dict[str, Any]]:
    """List notifications for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        q = (
            client.table("partner_notifications")
            .select("*")
            .eq("partner_id", partner_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if unread_only:
            q = q.eq("is_read", False)
        result = q.execute()
        return result.data or []
    except Exception:
        return []


async def mark_notification_read(notification_id: str, partner_id: str) -> bool:
    """Mark notification as read."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("partner_notifications").update({"is_read": True}).eq(
            "id", notification_id
        ).eq("partner_id", partner_id).execute()
        return True
    except Exception:
        return False


# --- Availability integrations ---
async def list_availability_integrations(partner_id: str) -> List[Dict[str, Any]]:
    """List availability integrations for a partner."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("availability_integrations")
            .select("*")
            .eq("partner_id", partner_id)
            .eq("is_active", True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


async def add_availability_integration(
    partner_id: str,
    integration_type: str,
    provider: Optional[str] = None,
    product_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Add availability integration."""
    client = get_supabase()
    if not client:
        return None
    try:
        row = {
            "partner_id": partner_id,
            "integration_type": integration_type,
            "provider": provider,
            "config": config or {},
        }
        if product_id:
            row["product_id"] = product_id
        result = client.table("availability_integrations").insert(row).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


# --- Order queue ---
async def list_partner_orders(
    partner_id: str,
    statuses: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List orders for a partner (via order_legs)."""
    client = get_supabase()
    if not client:
        return []
    statuses = statuses or ["pending", "accepted", "preparing", "ready"]
    try:
        legs = (
            client.table("order_legs")
            .select("*, orders(*)")
            .eq("partner_id", partner_id)
            .in_("status", statuses)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        if not legs.data:
            return []
        order_ids = list({str(l["order_id"]) for l in legs.data})
        items_res = (
            client.table("order_items")
            .select("*")
            .in_("order_id", order_ids)
            .eq("partner_id", partner_id)
            .execute()
        )
        items_by_order = {}
        for it in (items_res.data or []):
            oid = str(it["order_id"])
            if oid not in items_by_order:
                items_by_order[oid] = []
            items_by_order[oid].append(it)
        result = []
        for leg in legs.data:
            oid = str(leg["order_id"])
            order = leg.get("orders") or {}
            order["order_items"] = items_by_order.get(oid, [])
            result.append({
                "order": order,
                "leg": leg,
                "order_id": oid,
                "leg_id": str(leg["id"]),
            })
        return result
    except Exception as e:
        logger.warning("list_partner_orders error: %s", e)
        return []


async def get_order_leg(leg_id: str, partner_id: str) -> Optional[Dict[str, Any]]:
    """Get order leg by ID for partner."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("order_legs")
            .select("*, orders(*)")
            .eq("id", leg_id)
            .eq("partner_id", partner_id)
            .single()
            .execute()
        )
        return result.data
    except Exception:
        return None


async def accept_order_leg(
    leg_id: str, partner_id: str, preparation_mins: int
) -> Optional[Dict[str, Any]]:
    """Accept order leg, set preparation time."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("order_legs")
            .update({"status": "accepted", "preparation_mins": preparation_mins})
            .eq("id", leg_id)
            .eq("partner_id", partner_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def reject_order_leg(
    leg_id: str, partner_id: str, reject_reason: str
) -> Optional[Dict[str, Any]]:
    """Reject order leg with reason."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("order_legs")
            .update({"status": "rejected", "reject_reason": reject_reason})
            .eq("id", leg_id)
            .eq("partner_id", partner_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def update_order_leg_status(
    leg_id: str, partner_id: str, status: str, **kwargs: Any
) -> Optional[Dict[str, Any]]:
    """Update order leg status (preparing, ready, fulfilled)."""
    client = get_supabase()
    if not client:
        return None
    try:
        payload = {"status": status, **kwargs}
        result = (
            client.table("order_legs")
            .update(payload)
            .eq("id", leg_id)
            .eq("partner_id", partner_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None
