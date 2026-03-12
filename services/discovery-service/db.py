"""Supabase database client for discovery service."""

import uuid as uuid_module
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from supabase import create_client, Client

from config import settings
from packages.shared.discovery import is_browse_query

__all__ = [
    "get_supabase",
    "check_connection",
    "search_products",
    "get_distinct_experience_tags",
    "get_internal_agent_urls",
    "get_ucp_partners_with_tokens",
    "onboard_ucp_partner",
    "get_shopify_mcp_endpoints",
    "onboard_shopify_curated_partner",
    "get_partner_agent_slug_map",
    "resolve_masked_id",
    "mask_product_id",
    "mask_products",
    "get_product_by_id",
    "get_partner_by_id",
    "get_partners_by_ids",
    "get_platform_config_ranking",
    "get_admin_orchestration_settings",
    "get_composite_discovery_config",
    "get_partner_ratings_map",
    "get_active_sponsorships",
    "update_partner_last_acp_push",
    "update_products_last_acp_push",
    "get_products_for_acp_export",
    "add_product_to_bundle",
    "add_products_to_bundle_bulk",
    "get_bundle_by_id",
    "create_order_from_bundle",
    "create_bundle_from_ucp_items",
    "get_order_by_id",
    "update_order_status",
    "remove_from_bundle",
    "replace_product_in_bundle",
    "get_agent_action_models",
    "upsert_products_from_legacy",
    "get_platform_manifest_config",
    "create_or_get_experience_session",
    "get_experience_session_by_thread",
    "get_experience_session_legs",
    "upsert_experience_session_leg",
    "update_experience_session_leg_status",
    "create_experience_session_leg_override",
    "list_experience_sessions_admin",
    "get_experience_session_admin",
    "get_partners_available_to_customize",
    "get_partner_design_chat_url",
    "transition_legs_to_in_customization",
    "update_experience_session_leg_design_started",
    "get_sla_legs_for_re_sourcing",
    "create_sla_re_sourcing_pending",
    "get_sla_re_sourcing_pending_by_thread",
    "clear_sla_re_sourcing_pending",
    "update_experience_session_customization_partner",
]

_client: Optional[Client] = None


def _table_data(data: Any) -> List[Dict[str, Any]]:
    """Cast Supabase result.data to list of dicts for type safety."""
    if data is None:
        return []
    if isinstance(data, dict):
        return [dict(data)]
    if not isinstance(data, list):
        return []
    return [dict(r) for r in data if isinstance(r, dict)]


def _table_row(data: Any) -> Optional[Dict[str, Any]]:
    """First row of result.data as dict or None. Handles .single() returning a dict."""
    if data is None:
        return None
    if isinstance(data, dict):
        return dict(data)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return dict(data[0])
    return None


def get_supabase() -> Optional[Client]:
    """Get Supabase client. Returns None if not configured."""
    global _client
    if _client is not None:
        return _client
    if not getattr(settings, "supabase_configured", bool(settings.supabase_url and settings.supabase_key)):
        return None
    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


async def check_connection() -> bool:
    """Verify database connectivity."""
    client = get_supabase()
    if not client:
        return False
    try:
        # Simple query to verify connection
        result = client.table("products").select("id").limit(1).execute()
        return result.data is not None
    except Exception:
        return False


async def search_products(
    query: str,
    limit: int = 20,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
    experience_tag: Optional[str] = None,
    experience_tags: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search products by name/description.
    Uses simple text search for MVP; semantic search (pgvector) can be added later.
    When experience_tag is set, filter to products whose experience_tags JSONB contains that tag.
    When experience_tags (list) is set, filter to products that contain ALL tags (AND semantics).
    """
    client = get_supabase()
    if not client:
        return []

    tags_to_apply: List[str] = []
    if experience_tags:
        tags_to_apply = [str(t).strip() for t in experience_tags if t and str(t).strip()]
    if not tags_to_apply and experience_tag and experience_tag.strip():
        tags_to_apply = [experience_tag.strip()]

    select_cols = (
        "id, name, description, price, currency, capabilities, metadata, partner_id, "
        "url, brand, image_url, is_eligible_search, is_eligible_checkout, target_countries, availability, experience_tags, created_at"
    )
    try:
        q = (
            client.table("products")
            .select(f"{select_cols}, sold_count")
            .is_("deleted_at", "null")
        )
        if query and not is_browse_query(query):
            pattern = f"%{query}%"
            q = q.or_(f"name.ilike.{pattern},description.ilike.{pattern}")
        if partner_id:
            q = q.eq("partner_id", partner_id)
        if exclude_partner_id:
            q = q.neq("partner_id", exclude_partner_id)
        for tag in tags_to_apply:
            q = q.contains("experience_tags", [tag])
        result = q.order("created_at", desc=True).limit(limit).execute()
        data = _table_data(result.data)
        for row in data:
            if "sold_count" not in row:
                row["sold_count"] = 0
        # Fallback: when name/description search returns nothing, match by capability (e.g. "flowers", "chocolates")
        if not data and query and not is_browse_query(query) and query.strip():
            data = await _search_products_by_capability(
                client, query.strip(), limit, select_cols,
                partner_id, exclude_partner_id, tags_to_apply,
            )
        return data
    except Exception:
        try:
            q = (
                client.table("products")
                .select(select_cols)
                .is_("deleted_at", "null")
            )
            if query and not is_browse_query(query):
                pattern = f"%{query}%"
                q = q.or_(f"name.ilike.{pattern},description.ilike.{pattern}")
            if partner_id:
                q = q.eq("partner_id", partner_id)
            if exclude_partner_id:
                q = q.neq("partner_id", exclude_partner_id)
            for tag in tags_to_apply:
                q = q.contains("experience_tags", [tag])
            result = q.order("created_at", desc=True).limit(limit).execute()
            data = _table_data(result.data)
            for row in data:
                if "sold_count" not in row:
                    row["sold_count"] = 0
            if not data and query and not is_browse_query(query) and query.strip():
                data = await _search_products_by_capability(
                    client, query.strip(), limit, select_cols,
                    partner_id, exclude_partner_id, tags_to_apply,
                )
            return data
        except Exception:
            return []


async def _search_products_by_capability(
    client: Client,
    capability: str,
    limit: int,
    select_cols: str,
    partner_id: Optional[str] = None,
    exclude_partner_id: Optional[str] = None,
    experience_tags_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Return products whose capabilities JSONB array contains the given capability (e.g. 'flowers').
    Use a single token for capability: multi-word values (e.g. 'birthday gifts') can produce
    malformed array literals in Postgres; we use the first word only for the contains filter.
    """
    cap_clean = (capability or "").strip().lower()
    if not cap_clean:
        return []
    # Avoid 400: Supabase/PostgREST serializes .contains("capabilities", ["birthday gifts"]) as
    # capabilities=cs.{birthday gifts} which Postgres rejects. Use first word only for containment.
    if " " in cap_clean:
        cap_clean = cap_clean.split()[0]
    try:
        q = (
            client.table("products")
            .select(f"{select_cols}, sold_count")
            .is_("deleted_at", "null")
            .contains("capabilities", [cap_clean])
        )
        if partner_id:
            q = q.eq("partner_id", partner_id)
        if exclude_partner_id:
            q = q.neq("partner_id", exclude_partner_id)
        if experience_tags_filter:
            for tag in experience_tags_filter:
                q = q.contains("experience_tags", [tag])
        result = q.order("created_at", desc=True).limit(limit).execute()
        data = _table_data(result.data)
        for row in data:
            if "sold_count" not in row:
                row["sold_count"] = 0
        return data
    except Exception:
        return []


async def get_distinct_experience_tags() -> List[str]:
    """Return distinct experience_tags values from products (for experience-categories API)."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = client.rpc("get_distinct_experience_tags").execute()
        data = _table_data(result.data)
        return [str(row.get("tag", "")).strip() for row in data if row.get("tag")]
    except Exception:
        return []


def _base_url_from_manifest_json(manifest: Dict[str, Any]) -> Optional[str]:
    """
    Derive base URL from UCP manifest JSON.
    Expects ucp.services["dev.ucp.shopping"].rest.endpoint (e.g. https://store.com/api/v1/ucp)
    or similar; returns origin (e.g. https://store.com).
    """
    try:
        ucp = manifest.get("ucp", manifest)
        if not isinstance(ucp, dict):
            return None
        services = ucp.get("services", {})
        if not isinstance(services, dict):
            return None
        dev = services.get("dev.ucp.shopping", services)
        if isinstance(dev, dict):
            dev = dev.get("rest", dev)
        if not isinstance(dev, dict):
            return None
        endpoint = dev.get("endpoint", dev.get("catalog", ""))
        if not endpoint or not isinstance(endpoint, str):
            return None
        endpoint = endpoint.strip().rstrip("/")
        if not endpoint.startswith("http"):
            endpoint = "https://" + endpoint
        from urllib.parse import urlparse
        parsed = urlparse(endpoint)
        base = f"{parsed.scheme or 'https'}://{parsed.netloc}"
        return base.rstrip("/") if base else None
    except Exception:
        return None


async def onboard_ucp_partner(
    base_url: str,
    display_name: str,
    price_premium_percent: float = 0.0,
    available_to_customize: bool = False,
    access_token: Optional[str] = None,
    access_token_vault_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Add or update a UCP partner in internal_agent_registry.
    Discovery will fetch /.well-known/ucp.json from base_url for catalog.
    Optional: price_premium_percent, available_to_customize, access_token (stored in Vault).
    """
    client = get_supabase()
    if not client:
        return {"error": "Database not configured", "registry_id": None}
    base_url = str(base_url).strip().rstrip("/")
    if not base_url:
        return {"error": "base_url required", "registry_id": None}
    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    display_name = (display_name or base_url).strip()

    vault_ref = access_token_vault_ref
    if access_token and not vault_ref:
        try:
            secret_name = f"ucp_{base_url.replace('https://', '').replace('http://', '').replace('/', '_')}_{uuid_module.uuid4().hex[:8]}"
            r = client.rpc("insert_shopify_token", {"secret_name": secret_name, "secret_value": access_token}).execute()
            if r.data is not None:
                vault_ref = str(r.data) if not isinstance(r.data, dict) else str(r.data.get("id", r.data))
        except Exception as e:
            return {"error": f"Failed to store token in Vault: {e}", "registry_id": None}

    try:
        now = datetime.now(timezone.utc).isoformat()
        existing = (
            client.table("internal_agent_registry")
            .select("id")
            .eq("base_url", base_url)
            .eq("transport_type", "UCP")
            .limit(1)
            .execute()
        )
        row = _table_row(existing.data)
        payload: Dict[str, Any] = {
            "display_name": display_name,
            "price_premium_percent": float(price_premium_percent),
            "available_to_customize": bool(available_to_customize),
            "updated_at": now,
        }
        if vault_ref:
            payload["access_token_vault_ref"] = vault_ref
        if row:
            client.table("internal_agent_registry").update(payload).eq("id", row["id"]).execute()
            return {"registry_id": str(row["id"]), "base_url": base_url}
        ins_payload: Dict[str, Any] = {
            "capability": "discovery",
            "base_url": base_url,
            "display_name": display_name,
            "enabled": True,
            "transport_type": "UCP",
            "price_premium_percent": float(price_premium_percent),
            "available_to_customize": bool(available_to_customize),
        }
        if vault_ref:
            ins_payload["access_token_vault_ref"] = vault_ref
        ins = client.table("internal_agent_registry").insert(ins_payload).execute()
        reg_data = _table_data(ins.data)
        registry_id = str(reg_data[0]["id"]) if reg_data else None
        return {"registry_id": registry_id, "base_url": base_url}
    except Exception as e:
        return {"error": str(e), "registry_id": None}


async def get_internal_agent_urls(capability: Optional[str] = None) -> List[str]:
    """
    Return list of internal Business Agent base URLs for UCP manifest discovery.
    Only returns rows with transport_type = 'UCP' (or null for backward compat).
    Used only server-side by Scout; never expose these URLs in responses.
    """
    client = get_supabase()
    if not client:
        return []
    try:
        q = (
            client.table("internal_agent_registry")
            .select("base_url")
            .eq("enabled", True)
            .or_("transport_type.eq.UCP,transport_type.is.null")
        )
        if capability and str(capability).strip():
            q = q.eq("capability", str(capability).strip())
        result = q.execute()
        data = _table_data(result.data)
        urls = [str(r.get("base_url", "")).strip() for r in data if r.get("base_url")]
        return [u for u in urls if u]
    except Exception:
        return []


async def get_ucp_partners_with_tokens(capability: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return UCP partners with optional access token for MCP auth.
    Each entry: { "base_url": str, "access_token": str | None }.
    When access_token_vault_ref is set, resolves token via get_shopify_token RPC (same vault).
    Used by Scout so MCP requests can send Authorization: Bearer when partner requires it.
    """
    client = get_supabase()
    if not client:
        return []
    try:
        q = (
            client.table("internal_agent_registry")
            .select("base_url, access_token_vault_ref")
            .eq("enabled", True)
            .or_("transport_type.eq.UCP,transport_type.is.null")
        )
        if capability and str(capability).strip():
            q = q.eq("capability", str(capability).strip())
        result = q.execute()
        data = _table_data(result.data)
        out: List[Dict[str, Any]] = []
        for r in data:
            base_url = (r.get("base_url") or "").strip()
            if not base_url:
                continue
            vault_ref = r.get("access_token_vault_ref")
            access_token: Optional[str] = None
            if vault_ref and str(vault_ref).strip():
                try:
                    rpc = client.rpc("get_shopify_token", {"vault_ref": str(vault_ref).strip()}).execute()
                    if rpc.data is not None and isinstance(rpc.data, str) and rpc.data.strip():
                        access_token = rpc.data.strip()
                except Exception:
                    pass
            out.append({"base_url": base_url, "access_token": access_token})
        return out
    except Exception:
        return []


async def get_shopify_mcp_endpoints(capability: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return Shopify MCP endpoints with slug and price_premium_percent for ShopifyMCPDriver.
    Each entry: { "mcp_endpoint": str, "slug": str, "price_premium_percent": float, "shop_url": str }.
    """
    client = get_supabase()
    if not client:
        return []
    try:
        q = client.table("shopify_curated_partners").select(
            "mcp_endpoint, shop_url, price_premium_percent, internal_agent_registry_id"
        )
        result = q.execute()
        data = _table_data(result.data)
        reg_ids = [r.get("internal_agent_registry_id") for r in data if r.get("internal_agent_registry_id")]
        reg_map: Dict[str, Dict[str, Any]] = {}
        if reg_ids:
            reg_res = client.table("internal_agent_registry").select("id, display_name, capability, enabled").in_("id", reg_ids).execute()
            for r in _table_data(reg_res.data):
                reg_map[str(r.get("id", ""))] = r
        import re
        out: List[Dict[str, Any]] = []
        for row in data:
            reg_id = row.get("internal_agent_registry_id")
            reg = reg_map.get(str(reg_id), {}) if reg_id else {}
            if not reg.get("enabled", True):
                continue
            if capability and str(capability).strip() and reg.get("capability") != str(capability).strip():
                continue
            display_name = (reg.get("display_name") or row.get("shop_url", "") or "shopify").strip()
            s = str(display_name).strip().lower()
            s = re.sub(r"[^a-z0-9]+", "_", s)
            slug = (s.strip("_") or "shopify")[:64]
            mcp = (row.get("mcp_endpoint") or "").strip()
            if not mcp:
                continue
            out.append({
                "mcp_endpoint": mcp,
                "slug": slug,
                "price_premium_percent": float(row.get("price_premium_percent") or 0),
                "shop_url": str(row.get("shop_url", "")).strip(),
            })
        return out
    except Exception:
        return []


async def onboard_shopify_curated_partner(
    shop_url: str,
    mcp_endpoint: str,
    display_name: str,
    supported_capabilities: List[str],
    available_to_customize: bool = False,
    price_premium_percent: float = 0.0,
    access_token: Optional[str] = None,
    access_token_vault_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create or update partner, internal_agent_registry, and shopify_curated_partners.
    Stores access_token in Vault via insert_shopify_token RPC when provided.
    """
    client = get_supabase()
    if not client:
        return {"error": "Database not configured", "partner_id": None, "registry_id": None}

    vault_ref = access_token_vault_ref
    if access_token and not vault_ref:
        try:
            secret_name = f"shopify_{shop_url.replace('.', '_')}_{uuid_module.uuid4().hex[:8]}"
            r = client.rpc("insert_shopify_token", {"secret_name": secret_name, "secret_value": access_token}).execute()
            if r.data is not None:
                vault_ref = str(r.data) if not isinstance(r.data, dict) else str(r.data.get("id", r.data))
        except Exception as e:
            return {"error": f"Failed to store token in Vault: {e}", "partner_id": None, "registry_id": None}

    if not vault_ref and access_token:
        return {"error": "Vault storage failed; no vault_ref returned", "partner_id": None, "registry_id": None}

    try:
        existing = client.table("shopify_curated_partners").select("id, partner_id, internal_agent_registry_id").eq("shop_url", shop_url).execute()
        existing_row = _table_row(existing.data) if existing.data else None

        partner_id: Optional[str] = None
        registry_id: Optional[str] = None

        if existing_row:
            partner_id = str(existing_row.get("partner_id", "")) if existing_row.get("partner_id") else None
            registry_id = str(existing_row.get("internal_agent_registry_id", "")) if existing_row.get("internal_agent_registry_id") else None

        if not partner_id:
            p_ins = client.table("partners").insert({
                "business_name": display_name,
                "contact_email": f"shopify-{shop_url}@uso.local",
                "verification_status": "verified",
                "trust_score": 80,
                "is_active": True,
            }).execute()
            partner_data = _table_data(p_ins.data)
            partner_id = str(partner_data[0]["id"]) if partner_data else None
            if not partner_id:
                return {"error": "Failed to create partner", "partner_id": None, "registry_id": None}

        base_url = mcp_endpoint.rstrip("/").rsplit("/", 1)[0] if "/" in mcp_endpoint else mcp_endpoint

        if not registry_id:
            reg_ins = client.table("internal_agent_registry").insert({
                "capability": "discovery",
                "base_url": base_url,
                "display_name": display_name,
                "enabled": True,
                "transport_type": "SHOPIFY",
                "available_to_customize": available_to_customize,
                "metadata": {"shop_url": shop_url, "mcp_endpoint": mcp_endpoint, "capabilities": supported_capabilities},
            }).execute()
            reg_data = _table_data(reg_ins.data)
            registry_id = str(reg_data[0]["id"]) if reg_data else None
            if not registry_id:
                return {"error": "Failed to create registry entry", "partner_id": partner_id, "registry_id": None}
        else:
            client.table("internal_agent_registry").update({
                "display_name": display_name,
                "available_to_customize": available_to_customize,
                "metadata": {"shop_url": shop_url, "mcp_endpoint": mcp_endpoint, "capabilities": supported_capabilities},
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", registry_id).execute()

        scp_payload: Dict[str, Any] = {
            "partner_id": partner_id,
            "internal_agent_registry_id": registry_id,
            "shop_url": shop_url,
            "mcp_endpoint": mcp_endpoint,
            "supported_capabilities": supported_capabilities,
            "price_premium_percent": price_premium_percent,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if vault_ref:
            scp_payload["access_token_vault_ref"] = vault_ref

        if existing_row:
            client.table("shopify_curated_partners").update(scp_payload).eq("shop_url", shop_url).execute()
        else:
            scp_payload.pop("updated_at", None)
            client.table("shopify_curated_partners").insert(scp_payload).execute()

        return {"partner_id": partner_id, "registry_id": registry_id, "shop_url": shop_url}
    except Exception as e:
        return {"error": str(e), "partner_id": None, "registry_id": None}


def _mask_id_insert(
    internal_product_id: str,
    partner_id: Optional[str],
    source: Optional[str],
    agent_slug: Optional[str] = None,
) -> Optional[str]:
    """
    Insert one mapping and return masked_id.
    When agent_slug provided: uso_{agent_slug}_{short_id}; else legacy uso_{24hex}.
    """
    client = get_supabase()
    if not client:
        return None
    short_uid = str(uuid_module.uuid4()).replace("-", "")[:16]
    if agent_slug:
        slug_safe = "".join(c for c in str(agent_slug) if c.isalnum() or c == "_")[:64] or "discovery"
        masked_id = f"uso_{slug_safe}_{short_uid}"
    else:
        masked_id = "uso_" + short_uid + str(uuid_module.uuid4()).replace("-", "")[:8]
    payload: Dict[str, Any] = {
        "masked_id": masked_id,
        "internal_product_id": str(internal_product_id),
        "partner_id": str(partner_id) if partner_id else None,
        "source": str(source) if source else None,
    }
    if agent_slug:
        payload["agent_slug"] = str(agent_slug)[:64]
    try:
        client.table("id_masking_map").insert(payload).execute()
        return masked_id
    except Exception:
        return None


async def get_partner_agent_slug_map(partner_ids: List[str]) -> Dict[str, str]:
    """
    Batch lookup agent_slug for partner_ids.
    Shopify partners: slug from shopify_curated_partners + internal_agent_registry (display_name).
    Regular partners: slug from partners.business_name sanitized.
    """
    if not partner_ids:
        return {}
    client = get_supabase()
    if not client:
        return {}
    partner_ids = [str(p).strip() for p in partner_ids if p]
    if not partner_ids:
        return {}
    out: Dict[str, str] = {}
    import re
    try:
        # Shopify: partner_id -> slug via shopify_curated_partners + registry
        scp = client.table("shopify_curated_partners").select(
            "partner_id, internal_agent_registry_id"
        ).in_("partner_id", partner_ids).execute()
        scp_data = _table_data(scp.data)
        reg_ids = list({str(r.get("internal_agent_registry_id", "")) for r in scp_data if r.get("internal_agent_registry_id")})
        reg_map: Dict[str, str] = {}
        if reg_ids:
            reg_res = client.table("internal_agent_registry").select(
                "id, display_name"
            ).in_("id", reg_ids).execute()
            for r in _table_data(reg_res.data):
                dn = (r.get("display_name") or "").strip()
                s = re.sub(r"[^a-z0-9]+", "_", dn.lower())
                reg_map[str(r.get("id", ""))] = (s.strip("_") or "shopify")[:64]
        for r in scp_data:
            pid = str(r.get("partner_id", ""))
            reg_id = str(r.get("internal_agent_registry_id", ""))
            if pid and reg_id and reg_map.get(reg_id):
                out[pid] = reg_map[reg_id]
        # Regular partners: business_name -> slug
        remaining = [p for p in partner_ids if p not in out]
        if remaining:
            p_res = client.table("partners").select(
                "id, business_name"
            ).in_("id", remaining).execute()
            for r in _table_data(p_res.data):
                pid = str(r.get("id", ""))
                bn = (r.get("business_name") or "").strip()
                s = re.sub(r"[^a-z0-9]+", "_", bn.lower())
                out[pid] = (s.strip("_") or "partner")[:64]
    except Exception:
        pass
    return out


async def mask_product_id(
    internal_product_id: str,
    partner_id: Optional[str] = None,
    source: Optional[str] = None,
    agent_slug: Optional[str] = None,
) -> Optional[str]:
    """Create masked id for internal product; store mapping. Returns uso_* id or None."""
    return _mask_id_insert(internal_product_id, partner_id, source, agent_slug)


def resolve_masked_id(masked_id: str) -> Optional[tuple]:
    """
    Resolve masked id to (internal_product_id, partner_id).
    Returns None if not found, not a masked id, or expired (expires_at in the past).
    """
    if not masked_id or not str(masked_id).startswith("uso_"):
        return None
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("id_masking_map")
            .select("internal_product_id, partner_id, expires_at")
            .eq("masked_id", str(masked_id))
            .limit(1)
            .execute()
        )
        row = _table_row(result.data)
        if not row:
            return None
        expires_at = row.get("expires_at")
        if expires_at:
            exp_dt: Optional[datetime] = None
            if isinstance(expires_at, str):
                try:
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                except Exception:
                    pass
            elif hasattr(expires_at, "tzinfo"):
                exp_dt = expires_at  # type: ignore[assignment]
            if exp_dt is not None and exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if exp_dt is not None and exp_dt < datetime.now(timezone.utc):
                return None
        return (str(row.get("internal_product_id", "")), row.get("partner_id"))
    except Exception:
        return None


async def mask_products(
    products: List[Dict[str, Any]],
    source: str = "local",
    agent_slug_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Replace each product's id with a masked id (uso_*); store mapping.
    Removes partner_id from each product so internal identifiers are not exposed.
    When agent_slug_map is None, looks up slugs from partner_id via get_partner_agent_slug_map.
    Returns new list of product dicts (shallow copy with id/partner_id updated).
    """
    if not products:
        return []
    client = get_supabase()
    if not client:
        return products
    if agent_slug_map is None:
        partner_ids = list({str(p.get("partner_id", "")) for p in products if p.get("partner_id")})
        agent_slug_map = await get_partner_agent_slug_map(partner_ids)
    out = []
    for p in products:
        internal_id = str(p.get("id", ""))
        if not internal_id:
            out.append(dict(p))
            continue
        partner_id = p.get("partner_id")
        agent_slug = agent_slug_map.get(str(partner_id or "")) if partner_id else None
        masked = _mask_id_insert(internal_id, partner_id, source, agent_slug)
        if masked:
            new_p = {k: v for k, v in p.items() if k != "partner_id"}
            new_p["id"] = masked
            out.append(new_p)
        else:
            new_p = dict(p)
            new_p.pop("partner_id", None)
            out.append(new_p)
    return out


async def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Get a single product by ID."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("products")
            .select(
                "id, name, description, price, currency, capabilities, metadata, partner_id, "
                "url, brand, image_url, is_eligible_search, is_eligible_checkout, target_countries, availability, experience_tags"
            )
            .eq("id", product_id)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return _table_row(result.data)
    except Exception:
        return None


async def get_partner_by_id(partner_id: str) -> Optional[Dict[str, Any]]:
    """Get partner by ID with seller attribution and last_acp_push_at."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("partners")
            .select(
                "id, business_name, seller_name, seller_url, return_policy_url, "
                "privacy_policy_url, terms_url, store_country, target_countries, last_acp_push_at, trust_score"
            )
            .eq("id", partner_id)
            .limit(1)
            .execute()
        )
        return _table_row(result.data)
    except Exception:
        return None


async def get_partners_by_ids(partner_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get partners by IDs for ranking (includes trust_score)."""
    if not partner_ids:
        return {}
    client = get_supabase()
    if not client:
        return {}
    try:
        result = (
            client.table("partners")
            .select("id, business_name, trust_score")
            .in_("id", partner_ids)
            .execute()
        )
        return {str(r["id"]): r for r in _table_data(result.data)}
    except Exception:
        return {}


async def get_platform_config_ranking() -> Optional[Dict[str, Any]]:
    """Get platform config for ranking (ranking_enabled, ranking_policy, ranking_edge_cases, sponsorship_pricing)."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("platform_config")
            .select("ranking_enabled, ranking_policy, ranking_edge_cases, sponsorship_pricing")
            .limit(1)
            .execute()
        )
        row = _table_row(result.data)
        if not row:
            return {"ranking_enabled": True}
        return dict(row)
    except Exception:
        return {"ranking_enabled": True}


async def get_admin_orchestration_settings() -> Optional[Dict[str, Any]]:
    """Get admin orchestration settings (global_tone, model_temperature, autonomy_level, discovery_timeout_ms)."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("admin_orchestration_settings")
            .select("global_tone, model_temperature, autonomy_level, discovery_timeout_ms")
            .limit(1)
            .execute()
        )
        row = _table_row(result.data)
        return dict(row) if row else None
    except Exception:
        return None


async def get_composite_discovery_config() -> Optional[Dict[str, Any]]:
    """Get composite_discovery_config from platform_config (products_per_category, product_mix, sponsorship_enabled)."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("platform_config")
            .select("composite_discovery_config")
            .limit(1)
            .execute()
        )
        row = _table_row(result.data)
        cdc = (row or {}).get("composite_discovery_config")
        return cdc if isinstance(cdc, dict) else None
    except Exception:
        return None


async def get_partner_ratings_map(partner_ids: List[str]) -> Dict[str, float]:
    """Get avg_rating per partner from partner_ratings."""
    if not partner_ids:
        return {}
    client = get_supabase()
    if not client:
        return {}
    try:
        result = (
            client.table("partner_ratings")
            .select("partner_id, avg_rating")
            .in_("partner_id", partner_ids)
            .execute()
        )
        data = _table_data(result.data)
        return {str(r["partner_id"]): float(r.get("avg_rating") or 0) for r in data}
    except Exception:
        return {}


def _valid_uuids(ids: List[str]) -> List[str]:
    """Filter to IDs that are valid UUIDs (product_sponsorships.product_id is UUID; UCP/Shopify gids are not)."""
    out = []
    for s in ids:
        if not s or not isinstance(s, str):
            continue
        s = s.strip()
        if not s:
            continue
        try:
            uuid_module.UUID(s)
            out.append(s)
        except (ValueError, TypeError):
            continue
    return out


async def get_active_sponsorships(product_ids: List[str]) -> set:
    """Get product IDs with active sponsorships (start_at <= now <= end_at, status=active).
    Only queries for valid UUID product_ids; UCP/Shopify external IDs (e.g. gid://shopify/...) are skipped to avoid 400."""
    if not product_ids:
        return set()
    uuids = _valid_uuids(product_ids)
    if not uuids:
        return set()
    client = get_supabase()
    if not client:
        return set()
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        result = (
            client.table("product_sponsorships")
            .select("product_id")
            .in_("product_id", uuids)
            .eq("status", "active")
            .lte("start_at", now)
            .gte("end_at", now)
            .execute()
        )
        return {str(r.get("product_id", "")) for r in _table_data(result.data) if r.get("product_id")}
    except Exception:
        return set()


async def update_partner_last_acp_push(partner_id: str) -> bool:
    """Set last_acp_push_at to now for 15-minute throttle."""
    client = get_supabase()
    if not client:
        return False
    try:
        from datetime import datetime, timezone
        client.table("partners").update({
            "last_acp_push_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", partner_id).execute()
        return True
    except Exception:
        return False


async def update_products_last_acp_push(product_ids: List[str], success: bool) -> bool:
    """Set last_acp_push_at and last_acp_push_success for given products (for portal status)."""
    if not product_ids:
        return True
    client = get_supabase()
    if not client:
        return False
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        for pid in product_ids:
            client.table("products").update({
                "last_acp_push_at": now,
                "last_acp_push_success": success,
                "updated_at": now,
            }).eq("id", pid).execute()
        return True
    except Exception:
        return False


async def get_products_for_acp_export(
    partner_id: Optional[str] = None,
    product_id: Optional[str] = None,
    product_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Get products with partner seller fields joined for ACP feed building.
    Returns list of product dicts each with partner seller_* merged (seller_name, seller_url, etc.).
    """
    client = get_supabase()
    if not client:
        return []
    try:
        q = (
            client.table("products")
            .select(
                "id, name, description, price, currency, capabilities, metadata, partner_id, "
                "url, brand, image_url, is_eligible_search, is_eligible_checkout, target_countries, availability, experience_tags"
            )
            .is_("deleted_at", "null")
        )
        if partner_id:
            q = q.eq("partner_id", partner_id)
        if product_id:
            q = q.eq("id", product_id)
        elif product_ids:
            q = q.in_("id", product_ids)
        result = q.execute()
        products = _table_data(result.data)
        if not products:
            return []
        partner_ids = list({str(p["partner_id"]) for p in products if p.get("partner_id")})
        partners_map = {}
        for pid in partner_ids:
            partner = await get_partner_by_id(pid)
            if partner:
                partners_map[pid] = partner
        out = []
        for p in products:
            row = dict(p)
            pid = str(p.get("partner_id", "")) if p.get("partner_id") else ""
            partner = partners_map.get(pid) if pid else None
            if partner:
                row["seller_name"] = partner.get("seller_name") or partner.get("business_name")
                row["seller_url"] = partner.get("seller_url")
                row["return_policy"] = partner.get("return_policy_url")
                row["seller_privacy_policy"] = partner.get("privacy_policy_url")
                row["seller_tos"] = partner.get("terms_url")
                row["store_country"] = partner.get("store_country")
                if partner.get("target_countries") is not None and "target_countries" not in row or row.get("target_countries") is None:
                    row["target_countries"] = partner.get("target_countries")
            out.append(row)
        return out
    except Exception:
        return []


async def add_product_to_bundle(
    product_id: str,
    user_id: Optional[str] = None,
    bundle_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Add product to bundle. Creates new draft bundle if bundle_id not provided.
    If product_id is masked (uso_*), resolve to internal id before lookup.
    Returns bundle with updated info.
    """
    client = get_supabase()
    if not client:
        return None

    internal_id = product_id
    if str(product_id).startswith("uso_"):
        resolved = resolve_masked_id(product_id)
        if resolved:
            internal_id = resolved[0]
        else:
            return None

    product = await get_product_by_id(internal_id)
    if not product:
        return None

    price = float(product.get("price", 0))
    partner_id = product.get("partner_id")

    try:
        if bundle_id:
            # Add to existing bundle
            seq_result = (
                client.table("bundle_legs")
                .select("leg_sequence")
                .eq("bundle_id", bundle_id)
                .order("leg_sequence", desc=True)
                .limit(1)
                .execute()
            )
            seq_row = _table_row(seq_result.data)
            next_seq = (int(seq_row.get("leg_sequence", 0)) + 1) if seq_row else 1

            bundle = (
                client.table("bundles")
                .select("*")
                .eq("id", bundle_id)
                .single()
                .execute()
            )
            bundle_row = _table_row(bundle.data)
            if not bundle_row:
                return None
            total = float(bundle_row.get("total_price") or 0) + price

            client.table("bundle_legs").insert({
                "bundle_id": bundle_id,
                "leg_sequence": next_seq,
                "product_id": internal_id,
                "partner_id": partner_id,
                "leg_type": "product",
                "price": price,
            }).execute()

            client.table("bundles").update({"total_price": total}).eq("id", bundle_id).execute()

            if thread_id and partner_id:
                session = await create_or_get_experience_session(thread_id, user_id)
                if session:
                    await upsert_experience_session_leg(
                        str(session["id"]),
                        str(partner_id),
                        product_id,
                        status="ready",
                    )
            return {
                "bundle_id": bundle_id,
                "product_added": product.get("name"),
                "total_price": total,
                "currency": bundle_row.get("currency") or "USD",
            }
        else:
            # Create new draft bundle
            # user_id must be a valid UUID referencing users(id); omit if not (e.g. "test-user")
            bundle_user_id = None
            if user_id:
                try:
                    uid = uuid_module.UUID(str(user_id))
                    bundle_user_id = str(uid)
                except (ValueError, TypeError):
                    pass
            bundle_row = {
                "bundle_name": "Chat Bundle",
                "total_price": price,
                "currency": product.get("currency", "USD"),
                "status": "draft",
            }
            if bundle_user_id:
                bundle_row["user_id"] = bundle_user_id
            bundle_result = client.table("bundles").insert(bundle_row).execute()
            first_row = _table_row(bundle_result.data)
            if not first_row:
                return None
            new_bundle_id = first_row.get("id")

            client.table("bundle_legs").insert({
                "bundle_id": new_bundle_id,
                "leg_sequence": 1,
                "product_id": internal_id,
                "partner_id": partner_id,
                "leg_type": "product",
                "price": price,
            }).execute()

            if thread_id and partner_id:
                session = await create_or_get_experience_session(thread_id, user_id)
                if session:
                    await upsert_experience_session_leg(
                        str(session["id"]),
                        str(partner_id),
                        product_id,
                        status="ready",
                    )
            return {
                "bundle_id": new_bundle_id,
                "product_added": product.get("name"),
                "total_price": price,
                "currency": product.get("currency", "USD"),
            }
    except Exception:
        return None


async def add_products_to_bundle_bulk(
    product_ids: List[str],
    user_id: Optional[str] = None,
    bundle_id: Optional[str] = None,
    fulfillment_details: Optional[Dict[str, Any]] = None,
    thread_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Add multiple products to a bundle in one call.
    Creates new draft bundle if bundle_id not provided.
    Returns { bundle_id, products_added, total_price, currency }.
    """
    if not product_ids:
        return None
    client = get_supabase()
    if not client:
        return None

    products_added: List[str] = []
    total_price = 0.0
    currency = "USD"

    for i, product_id in enumerate(product_ids):
        result = await add_product_to_bundle(
            product_id=product_id,
            user_id=user_id if i == 0 and not bundle_id else None,
            bundle_id=bundle_id,
            thread_id=thread_id,
        )
        if not result:
            continue
        bundle_id = result.get("bundle_id")
        products_added.append(result.get("product_added", ""))
        total_price = float(result.get("total_price", 0))
        currency = result.get("currency", "USD")

    if not products_added or not bundle_id:
        return None
    if fulfillment_details:
        try:
            client.table("bundles").update({"fulfillment_details": fulfillment_details}).eq("id", bundle_id).execute()
        except Exception:
            pass
    return {
        "bundle_id": bundle_id,
        "products_added": products_added,
        "total_price": total_price,
        "currency": currency,
    }


async def get_bundle_by_id(bundle_id: str) -> Optional[Dict[str, Any]]:
    """
    Get bundle by ID with items (legs joined to products).
    Returns bundle dict with items array for Adaptive Card.
    """
    client = get_supabase()
    if not client:
        return None
    try:
        bundle_result = (
            client.table("bundles")
            .select("id, user_id, bundle_name, total_price, currency, status, created_at, fulfillment_details")
            .eq("id", bundle_id)
            .single()
            .execute()
        )
        bundle = _table_row(bundle_result.data)
        if not bundle:
            return None
        bundle = dict(bundle)

        legs_result = (
            client.table("bundle_legs")
            .select("id, leg_sequence, product_id, price")
            .eq("bundle_id", bundle_id)
            .order("leg_sequence")
            .execute()
        )
        legs = _table_data(legs_result.data)

        product_ids = [leg.get("product_id") for leg in legs if leg.get("product_id")]
        product_names: Dict[str, Dict[str, Any]] = {}
        if product_ids:
            products_result = (
                client.table("products")
                .select("id, name, currency, capabilities")
                .in_("id", product_ids)
                .execute()
            )
            for p in _table_data(products_result.data):
                product_names[str(p.get("id", ""))] = p

        currency = bundle.get("currency", "USD")
        items = []
        for leg in legs:
            pid = str(leg.get("product_id", ""))
            p = product_names.get(pid, {})
            caps = p.get("capabilities") or []
            if isinstance(caps, str):
                caps = [caps] if caps else []
            items.append({
                "id": str(leg.get("id", "")),
                "product_id": pid,
                "name": p.get("name", "Unknown"),
                "price": float(leg.get("price", 0)),
                "currency": p.get("currency", currency),
                "capabilities": caps,
            })

        bundle["items"] = items
        bundle["item_count"] = len(items)
        bundle["name"] = bundle.get("bundle_name") or "Your Bundle"
        return bundle
    except Exception:
        return None


async def create_order_from_bundle(bundle_id: str) -> Optional[Dict[str, Any]]:
    """
    Create order from bundle. Inserts into orders, order_items, order_legs.
    Returns order dict with id, bundle_id, total_amount, currency, status, line_items.
    For composite bundles (3+ items), requires fulfillment_details (pickup_time, pickup_address, delivery_address).
    """
    client = get_supabase()
    if not client:
        return None
    try:
        bundle = await get_bundle_by_id(bundle_id)
        if not bundle:
            return None
        items = bundle.get("items", [])
        if not items:
            return None
        # Composite bundles (3+ items) require fulfillment details before order acceptance
        if len(items) >= 3:
            fd = bundle.get("fulfillment_details") or {}
            required = fd.get("required_fields") or ["pickup_time", "pickup_address", "delivery_address"]
            missing = [f for f in required if not (fd.get(f) or "").strip()]
            if missing:
                return {"error": "fulfillment_required", "message": f"Missing required fulfillment: {', '.join(missing)}."}
        total = float(bundle.get("total_price", 0))
        currency = bundle.get("currency", "USD")
        user_id = bundle.get("user_id")

        order_result = client.table("orders").insert({
            "user_id": user_id,
            "bundle_id": bundle_id,
            "total_amount": total,
            "currency": currency,
            "status": "pending",
            "payment_status": "pending",
        }).execute()
        order_row = _table_row(order_result.data)
        if not order_row:
            return None
        order_id = str(order_row["id"])

        legs_result = (
            client.table("bundle_legs")
            .select("id, leg_sequence, product_id, partner_id, price")
            .eq("bundle_id", bundle_id)
            .order("leg_sequence")
            .execute()
        )
        legs = _table_data(legs_result.data)
        product_ids = [leg.get("product_id") for leg in legs if leg.get("product_id")]
        product_names: Dict[str, Any] = {}
        if product_ids:
            products_result = (
                client.table("products")
                .select("id, name, currency")
                .in_("id", product_ids)
                .execute()
            )
            for p in _table_data(products_result.data):
                product_names[str(p.get("id", ""))] = p.get("name", "Unknown")

        for leg in legs:
            product_id = leg.get("product_id")
            partner_id = leg.get("partner_id")
            price = float(leg.get("price", 0))
            item_name = product_names.get(str(product_id), "Unknown") if product_id else "Unknown"

            client.table("order_items").insert({
                "order_id": order_id,
                "product_id": product_id,
                "partner_id": partner_id,
                "item_name": item_name,
                "quantity": 1,
                "unit_price": price,
                "total_price": price,
            }).execute()

            client.table("order_legs").insert({
                "order_id": order_id,
                "bundle_leg_id": leg.get("id"),
                "partner_id": partner_id,
                "status": "pending",
            }).execute()

        # Create conversations for each partner (order linkage for AI support)
        partner_ids_seen = set()
        for leg in legs:
            pid = leg.get("partner_id")
            if pid and pid not in partner_ids_seen:
                partner_ids_seen.add(pid)
                try:
                    conv_r = client.table("conversations").insert({
                        "partner_id": pid,
                        "order_id": order_id,
                        "bundle_id": bundle_id,
                        "title": f"Order {order_id[:8]}...",
                        "status": "active",
                    }).select("id").execute()  # type: ignore[union-attr]
                    conv_row = _table_row(conv_r.data)
                    if conv_row and user_id:
                        client.table("participants").insert({
                            "conversation_id": conv_row.get("id"),
                            "user_id": user_id,
                            "participant_type": "customer",
                        }).execute()
                except Exception:
                    pass

        line_items = [
            {"name": product_names.get(str(leg.get("product_id")), "Unknown"), "quantity": 1, "price": float(leg.get("price", 0)), "currency": currency}
            for leg in legs
        ]
        return {
            "id": order_id,
            "bundle_id": bundle_id,
            "subtotal": total,
            "total": total,
            "currency": currency,
            "line_items": line_items,
            "status": "pending",
            "payment_status": "pending",
        }
    except Exception:
        return None


async def create_bundle_from_ucp_items(
    line_items: List[Dict[str, Any]],
    currency: str = "USD",
) -> Optional[str]:
    """
    Create a bundle from UCP line items. Each item: {item: {id: product_id}, quantity: int}.
    Returns bundle_id or None.
    """
    client = get_supabase()
    if not client or not line_items:
        return None
    try:
        bundle_result = client.table("bundles").insert({
            "bundle_name": "UCP Checkout",
            "total_price": 0,
            "currency": currency,
            "status": "draft",
        }).execute()
        first = _table_row(bundle_result.data)
        if not first:
            return None
        bundle_id = str(first.get("id", ""))
        total = 0.0
        seq = 1
        for li in line_items:
            item = li.get("item") or {}
            product_id = str(item.get("id", ""))
            qty = int(li.get("quantity", 1))
            if not product_id or qty < 1:
                continue
            internal_id = product_id
            if product_id.startswith("uso_"):
                resolved = resolve_masked_id(product_id)
                if resolved:
                    internal_id = resolved[0]
                else:
                    continue
            product = await get_product_by_id(internal_id)
            if not product:
                continue
            price = float(product.get("price", 0))
            partner_id = product.get("partner_id")
            for _ in range(qty):
                client.table("bundle_legs").insert({
                    "bundle_id": bundle_id,
                    "leg_sequence": seq,
                    "product_id": internal_id,
                    "partner_id": partner_id,
                    "leg_type": "product",
                    "price": price,
                }).execute()
                total += price
                seq += 1
        client.table("bundles").update({"total_price": total}).eq("id", bundle_id).execute()
        return bundle_id
    except Exception:
        return None


async def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Get order with line items for UCP checkout."""
    client = get_supabase()
    if not client:
        return None
    try:
        order_result = (
            client.table("orders")
            .select("id, bundle_id, user_id, total_amount, currency, status, payment_status, created_at")
            .eq("id", order_id)
            .single()
            .execute()
        )
        order = _table_row(order_result.data)
        if not order:
            return None
        order = dict(order)
        items_result = (
            client.table("order_items")
            .select("id, product_id, partner_id, item_name, quantity, unit_price, total_price")
            .eq("order_id", order_id)
            .execute()
        )
        order["items"] = _table_data(items_result.data)
        return order
    except Exception:
        return None


async def update_order_status(order_id: str, status: str, payment_status: Optional[str] = None) -> bool:
    """Update order status (and optionally payment_status)."""
    client = get_supabase()
    if not client:
        return False
    try:
        updates = {"status": status}
        if payment_status is not None:
            updates["payment_status"] = payment_status
        client.table("orders").update(updates).eq("id", order_id).execute()
        return True
    except Exception:
        return False


async def remove_from_bundle(item_id: str) -> Optional[Dict[str, Any]]:
    """
    Remove a bundle leg (item) by id. Updates bundle total_price.
    item_id is the bundle_leg id from the bundle card.
    """
    client = get_supabase()
    if not client:
        return None
    try:
        leg_result = (
            client.table("bundle_legs")
            .select("id, bundle_id, price")
            .eq("id", item_id)
            .single()
            .execute()
        )
        leg = _table_row(leg_result.data)
        if not leg:
            return None
        bundle_id = leg.get("bundle_id")
        price = float(leg.get("price", 0))

        bundle_result = (
            client.table("bundles")
            .select("total_price, currency")
            .eq("id", bundle_id)
            .single()
            .execute()
        )
        bundle_row = _table_row(bundle_result.data)
        if not bundle_row:
            return None
        total = float(bundle_row.get("total_price", 0)) - price
        total = max(0, total)

        client.table("bundle_legs").delete().eq("id", item_id).execute()
        client.table("bundles").update({"total_price": total}).eq("id", bundle_id).execute()

        return {
            "bundle_id": bundle_id,
            "item_removed_id": item_id,
            "total_price": total,
            "currency": bundle_row.get("currency", "USD"),
        }
    except Exception:
        return None


async def replace_product_in_bundle(
    bundle_id: str,
    leg_id_to_replace: str,
    new_product_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Replace a bundle leg with a new product. Removes old leg, adds new product.
    Returns updated bundle summary or None on failure.
    """
    remove_result = await remove_from_bundle(leg_id_to_replace)
    if not remove_result or remove_result.get("bundle_id") != bundle_id:
        return None
    add_result = await add_product_to_bundle(
        product_id=new_product_id,
        bundle_id=bundle_id,
    )
    if not add_result:
        return None
    return {
        "bundle_id": bundle_id,
        "leg_replaced": leg_id_to_replace,
        "product_added": add_result.get("product_added"),
        "total_price": add_result.get("total_price"),
        "currency": add_result.get("currency", "USD"),
    }


# --- Experience Sessions (Phase 4) ---


async def create_or_get_experience_session(
    thread_id: str,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create or return existing experience session for thread_id."""
    client = get_supabase()
    if not client:
        return None
    try:
        existing = (
            client.table("experience_sessions")
            .select("*")
            .eq("thread_id", str(thread_id))
            .limit(1)
            .execute()
        )
        row = _table_row(existing.data)
        if row:
            return row
        user_uuid = None
        if user_id:
            try:
                user_uuid = str(uuid_module.UUID(str(user_id)))
            except (ValueError, TypeError):
                pass
        ins = client.table("experience_sessions").insert({
            "thread_id": str(thread_id),
            "user_id": user_uuid,
            "status": "active",
        }).execute()
        return _table_row(ins.data)
    except Exception:
        return None


async def get_experience_session_by_thread(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get experience session by thread_id."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("experience_sessions")
            .select("*")
            .eq("thread_id", str(thread_id))
            .limit(1)
            .execute()
        )
        return _table_row(result.data)
    except Exception:
        return None


async def get_experience_session_legs(session_id: str) -> List[Dict[str, Any]]:
    """Get legs for experience session with partner names joined."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("experience_session_legs")
            .select(
                "id, partner_id, product_id, status, shopify_draft_order_id, "
                "external_order_id, external_reservation_id, vendor_type, allows_modification, "
                "design_started_at, customization_partner_id, created_at, updated_at"
            )
            .eq("experience_session_id", str(session_id))
            .order("created_at")
            .execute()
        )
        legs = _table_data(result.data)
        if not legs:
            return []
        partner_ids = list({str(l["partner_id"]) for l in legs if l.get("partner_id")})
        partners = await get_partners_by_ids(partner_ids)
        out = []
        for l in legs:
            row = dict(l)
            p = partners.get(str(l.get("partner_id", ""))) if l.get("partner_id") else None
            row["partner_name"] = p.get("business_name") or p.get("seller_name") if p else None
            out.append(row)
        return out
    except Exception:
        return []


async def upsert_experience_session_leg(
    session_id: str,
    partner_id: str,
    product_id: str,
    status: str = "ready",
) -> Optional[Dict[str, Any]]:
    """Create or update leg for session/partner/product. product_id is masked (uso_*)."""
    client = get_supabase()
    if not client:
        return None
    try:
        existing = (
            client.table("experience_session_legs")
            .select("id")
            .eq("experience_session_id", session_id)
            .eq("partner_id", partner_id)
            .eq("product_id", product_id)
            .limit(1)
            .execute()
        )
        row = _table_row(existing.data)
        now = datetime.now(timezone.utc).isoformat()
        if row:
            client.table("experience_session_legs").update({
                "status": status,
                "updated_at": now,
            }).eq("id", row["id"]).execute()
            return {"id": row["id"], "status": status}
        ins = client.table("experience_session_legs").insert({
            "experience_session_id": session_id,
            "partner_id": partner_id,
            "product_id": product_id,
            "status": status,
        }).execute()
        r = _table_row(ins.data)
        return r
    except Exception:
        return None


async def update_experience_session_leg_status(
    leg_id: str,
    new_status: str,
    admin_id: str,
) -> Optional[Dict[str, Any]]:
    """Update leg status and record override audit."""
    client = get_supabase()
    if not client:
        return None
    try:
        leg = (
            client.table("experience_session_legs")
            .select("id, status")
            .eq("id", leg_id)
            .limit(1)
            .execute()
        )
        row = _table_row(leg.data)
        if not row:
            return None
        old_status = row.get("status", "pending")
        now = datetime.now(timezone.utc).isoformat()
        client.table("experience_session_legs").update({
            "status": new_status,
            "updated_at": now,
        }).eq("id", leg_id).execute()
        client.table("experience_session_leg_overrides").insert({
            "leg_id": leg_id,
            "admin_id": admin_id,
            "old_status": old_status,
            "new_status": new_status,
        }).execute()
        return {"id": leg_id, "status": new_status}
    except Exception:
        return None


async def create_experience_session_leg_override(
    leg_id: str, admin_id: str, old_status: str, new_status: str
) -> bool:
    """Insert override audit row."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("experience_session_leg_overrides").insert({
            "leg_id": leg_id,
            "admin_id": admin_id,
            "old_status": old_status,
            "new_status": new_status,
        }).execute()
        return True
    except Exception:
        return False


async def list_experience_sessions_admin(
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List experience sessions for admin with optional filters."""
    client = get_supabase()
    if not client:
        return []
    try:
        q = client.table("experience_sessions").select("*")
        if thread_id:
            q = q.eq("thread_id", thread_id)
        if user_id:
            q = q.eq("user_id", user_id)
        if status:
            q = q.eq("status", status)
        result = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return _table_data(result.data)
    except Exception:
        return []


async def get_experience_session_admin(session_id: str) -> Optional[Dict[str, Any]]:
    """Get experience session by id for admin (with legs)."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("experience_sessions")
            .select("*")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )
        session = _table_row(result.data)
        if not session:
            return None
        legs = await get_experience_session_legs(session_id)
        session["legs"] = legs
        return session
    except Exception:
        return None


async def get_partners_available_to_customize(partner_ids: List[str]) -> set:
    """Return set of partner_ids that have available_to_customize (via shopify_curated_partners -> internal_agent_registry)."""
    if not partner_ids:
        return set()
    client = get_supabase()
    if not client:
        return set()
    try:
        result = (
            client.table("shopify_curated_partners")
            .select("partner_id, internal_agent_registry(available_to_customize)")
            .in_("partner_id", partner_ids)
            .execute()
        )
        out = set()
        for row in _table_data(result.data):
            reg = row.get("internal_agent_registry") if isinstance(row.get("internal_agent_registry"), dict) else {}
            if reg.get("available_to_customize"):
                out.add(str(row.get("partner_id", "")))
        return out
    except Exception:
        return set()


async def get_partner_design_chat_url(partner_id: str) -> Optional[str]:
    """Get design_chat_url for partner (shopify_curated_partners.design_chat_url or internal_agent_registry.design_chat_url)."""
    client = get_supabase()
    if not client:
        return None
    try:
        scp = (
            client.table("shopify_curated_partners")
            .select("design_chat_url, internal_agent_registry_id")
            .eq("partner_id", partner_id)
            .limit(1)
            .execute()
        )
        row = _table_row(scp.data)
        if row and row.get("design_chat_url"):
            return str(row["design_chat_url"]).strip()
        if row and row.get("internal_agent_registry_id"):
            reg = (
                client.table("internal_agent_registry")
                .select("design_chat_url")
                .eq("id", row["internal_agent_registry_id"])
                .limit(1)
                .execute()
            )
            r = _table_row(reg.data)
            if r and r.get("design_chat_url"):
                return str(r["design_chat_url"]).strip()
        return None
    except Exception:
        return None


async def transition_legs_to_in_customization(thread_id: str, order_id: str) -> int:
    """After payment: set legs to in_customization when partner has available_to_customize. Returns count updated."""
    client = get_supabase()
    if not client:
        return 0
    try:
        sess = (
            client.table("experience_sessions")
            .select("id")
            .eq("thread_id", thread_id)
            .limit(1)
            .execute()
        )
        if not sess.data or not sess.data[0]:
            return 0
        session_id = sess.data[0].get("id")
        legs = (
            client.table("experience_session_legs")
            .select("id, partner_id")
            .eq("experience_session_id", session_id)
            .eq("status", "ready")
            .execute()
        )
        if not legs.data:
            return 0
        partner_ids = list({str(l["partner_id"]) for l in legs.data if l.get("partner_id")})
        customizable = await get_partners_available_to_customize(partner_ids)
        now = datetime.now(timezone.utc).isoformat()
        count = 0
        for leg in legs.data:
            if str(leg.get("partner_id", "")) in customizable:
                client.table("experience_session_legs").update({
                    "status": "in_customization",
                    "updated_at": now,
                }).eq("id", leg["id"]).execute()
                count += 1
        return count
    except Exception:
        return 0


async def update_experience_session_leg_design_started(leg_id: str) -> bool:
    """Set design_started_at and allows_modification=false (Point of No Return)."""
    client = get_supabase()
    if not client:
        return False
    try:
        now = datetime.now(timezone.utc).isoformat()
        client.table("experience_session_legs").update({
            "design_started_at": now,
            "allows_modification": False,
            "updated_at": now,
        }).eq("id", leg_id).execute()
        return True
    except Exception:
        return False


async def get_sla_legs_for_re_sourcing() -> List[Dict[str, Any]]:
    """Find legs where SLA exceeded: ready/in_customization, partner has sla_response_hours, design_started_at NULL, re_sourcing_state not awaiting."""
    client = get_supabase()
    if not client:
        return []
    try:
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        legs = (
            client.table("experience_session_legs")
            .select("id, experience_session_id, partner_id, product_id, status, re_sourcing_state, created_at")
            .in_("status", ["ready", "in_customization"])
            .is_("design_started_at", "null")
            .neq("re_sourcing_state", "awaiting_user_response")
            .execute()
        )
        out = []
        for leg in legs.data or []:
            if leg.get("re_sourcing_state") == "awaiting_user_response":
                continue
            out.append(dict(leg))
        return out
    except Exception:
        return []


async def create_sla_re_sourcing_pending(leg_id: str, alternatives_snapshot: List[Dict[str, Any]]) -> Optional[str]:
    """Create sla_re_sourcing_pending record. Returns id."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = client.table("sla_re_sourcing_pending").insert({
            "experience_session_leg_id": leg_id,
            "alternatives_snapshot": alternatives_snapshot,
        }).execute()
        row = result.data[0] if result.data else None
        if row:
            client.table("experience_session_legs").update({
                "re_sourcing_state": "awaiting_user_response",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", leg_id).execute()
        return str(row["id"]) if row else None
    except Exception:
        return None


async def get_sla_re_sourcing_pending_by_thread(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get pending SLA re-sourcing for thread (session -> legs -> pending)."""
    client = get_supabase()
    if not client:
        return None
    try:
        sess = (
            client.table("experience_sessions")
            .select("id")
            .eq("thread_id", thread_id)
            .limit(1)
            .execute()
        )
        if not sess.data or not sess.data[0]:
            return None
        session_id = sess.data[0].get("id")
        legs = (
            client.table("experience_session_legs")
            .select("id")
            .eq("experience_session_id", session_id)
            .eq("re_sourcing_state", "awaiting_user_response")
            .execute()
        )
        if not legs.data:
            return None
        leg_id = legs.data[0].get("id")
        pending = (
            client.table("sla_re_sourcing_pending")
            .select("*")
            .eq("experience_session_leg_id", leg_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return _table_row(pending.data)
    except Exception:
        return None


async def clear_sla_re_sourcing_pending(leg_id: str) -> bool:
    """Clear re_sourcing_state and delete pending record."""
    client = get_supabase()
    if not client:
        return False
    try:
        client.table("experience_session_legs").update({
            "re_sourcing_state": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", leg_id).execute()
        client.table("sla_re_sourcing_pending").delete().eq("experience_session_leg_id", leg_id).execute()
        return True
    except Exception:
        return False


async def update_experience_session_customization_partner(
    session_id: str,
    customization_partner_id: Optional[str],
) -> bool:
    """Set customization_partner_id on experience session (hybrid customization)."""
    client = get_supabase()
    if not client:
        return False
    try:
        update = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if customization_partner_id:
            update["customization_partner_id"] = customization_partner_id
        else:
            update["customization_partner_id"] = None
        client.table("experience_sessions").update(update).eq("id", session_id).execute()
        return True
    except Exception:
        return False


# --- Module 3: AI-First Discoverability ---


async def get_agent_action_models() -> List[Dict[str, Any]]:
    """Get active action models for AI agents."""
    client = get_supabase()
    if not client:
        return []
    try:
        result = (
            client.table("agent_action_models")
            .select(
                "action_name, method, endpoint, requires_auth, requires_approval_if_over, "
                "rate_limit_per_hour, allowed_parameters, restricted_parameters, "
                "allowed_modifications, restricted_modifications"
            )
            .eq("is_active", True)
            .order("action_name")
            .execute()
        )
        return _table_data(result.data)
    except Exception:
        return []


async def upsert_products_from_legacy(
    partner_id: str,
    products: List[Dict[str, Any]],
    replace_legacy: bool = False,
) -> Dict[str, Any]:
    """
    Insert or upsert products from Legacy Adapter (Module 2).
    Normalized products are indexed for Scout Engine discovery.

    replace_legacy: If True, soft-delete existing products with metadata.source='legacy_adapter'
    for this partner before inserting. Prevents duplicates on re-import.
    """
    client = get_supabase()
    if not client:
        return {"inserted": 0, "updated": 0, "error": "Database not configured"}

    try:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        if replace_legacy:
            # Soft-delete existing legacy products for this partner
            all_rows = (
                client.table("products")
                .select("id, metadata")
                .eq("partner_id", partner_id)
                .is_("deleted_at", "null")
                .execute()
            )
            for row in _table_data(all_rows.data):
                meta = row.get("metadata") or {}
                if isinstance(meta, dict) and meta.get("source") == "legacy_adapter":
                    client.table("products").update({
                        "deleted_at": now,
                        "updated_at": now,
                    }).eq("id", row["id"]).execute()

        inserted = 0
        for p in products:
            legacy_id = p.get("id") or ""
            metadata = dict(p.get("metadata") or {})
            metadata["legacy_id"] = legacy_id
            row = {
                "partner_id": partner_id,
                "name": p.get("name") or "Unknown",
                "description": p.get("description") or "",
                "price": float(p.get("price", 0)),
                "currency": p.get("currency", "USD"),
                "capabilities": p.get("capabilities") or [],
                "metadata": metadata,
                "url": p.get("url"),
                "brand": p.get("brand"),
                "image_url": p.get("image_url"),
                "availability": p.get("availability", "in_stock"),
                "is_eligible_search": True,
                "is_eligible_checkout": False,
            }
            client.table("products").insert(row).execute()
            inserted += 1

        return {"inserted": inserted, "updated": 0}
    except Exception as e:
        return {"inserted": 0, "updated": 0, "error": str(e)}


async def get_platform_manifest_config() -> Optional[Dict[str, Any]]:
    """Get active platform manifest config."""
    client = get_supabase()
    if not client:
        return None
    try:
        result = (
            client.table("platform_manifest_config")
            .select("*")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return _table_row(result.data)
    except Exception:
        return None
