"""Admin endpoints for Module 1: manifest ingest, embedding backfill; Module 2: Legacy Adapter."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from config import settings
from db import get_supabase, upsert_products_from_legacy  # type: ignore[reportAttributeAccessIssue]
from manifest_cache import cache_partner_manifest
from semantic_search import (
    backfill_product_embedding,
    backfill_all_product_embeddings,
    backfill_kb_article_embedding,
    backfill_all_kb_article_embeddings,
)

from adapters.legacy_adapter import (
    parse_csv_to_products,
    parse_excel_to_products,
    parse_json_to_products,
    DEFAULT_COLUMN_MAP,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class ManifestIngestBody(BaseModel):
    """Request to ingest manifest from URL."""

    partner_id: str
    manifest_url: str
    manifest_type: str = "acp"  # "acp" | "ucp"
    validate_acp: bool = False  # If true and manifest_type=acp, only cache ACP-compliant products


class ShopifyPartnerOnboardBody(BaseModel):
    """Request to onboard a curated Shopify partner (MCP)."""

    shop_url: str
    access_token: Optional[str] = None
    access_token_vault_ref: Optional[str] = None
    mcp_endpoint: str
    supported_capabilities: List[str] = []
    display_name: str
    available_to_customize: bool = False
    price_premium_percent: float = 0.0


class UCPPartnerOnboardBody(BaseModel):
    """Request to onboard a UCP-only partner (manifest JSON or manual base_url)."""

    base_url: Optional[str] = None
    display_name: Optional[str] = None
    manifest_json: Optional[str] = None
    price_premium_percent: float = 0.0
    available_to_customize: bool = False
    access_token: Optional[str] = None
    access_token_vault_ref: Optional[str] = None


@router.post("/manifest/ingest")
async def ingest_manifest(body: ManifestIngestBody):
    """
    Fetch and cache partner manifest from URL.
    Parses via UCP or ACP adapter based on manifest_type.
    If validate_acp=True and manifest_type=acp, only compliant products are cached (per OpenAI Product Feed Spec).
    """
    products = await cache_partner_manifest(
        partner_id=body.partner_id,
        manifest_url=body.manifest_url,
        manifest_type=body.manifest_type,
    )
    if not products:
        return {"products_count": 0, "manifest_type": body.manifest_type, "acp_validated": False}

    if body.validate_acp and body.manifest_type.lower() == "acp":
        from protocols.acp_compliance import filter_acp_compliant_products

        products_list: List[Dict[str, Any]] = products if isinstance(products, list) else []
        compliant, non_compliant = filter_acp_compliant_products(products_list, strict=True)
        # Re-cache only compliant products (override manifest_data with compliant list)
        if compliant != products:
            from db import get_supabase
            from datetime import datetime, timedelta

            client = get_supabase()
            if client:
                expires_at = (datetime.utcnow() + timedelta(seconds=3600)).isoformat()
                payload = {
                    "partner_id": body.partner_id,
                    "manifest_url": body.manifest_url,
                    "manifest_type": body.manifest_type,
                    "manifest_data": {"products": compliant, "cached_at": datetime.utcnow().isoformat(), "acp_validated": True},
                    "expires_at": expires_at,
                    "last_validated_at": datetime.utcnow().isoformat(),
                    "validation_status": "valid",
                }
                existing = (
                    client.table("partner_manifests")
                    .select("id")
                    .eq("partner_id", body.partner_id)
                    .eq("manifest_url", body.manifest_url)
                    .execute()
                )
                existing_data = existing.data
                first_id = (
                    existing_data[0]["id"]
                    if isinstance(existing_data, list) and len(existing_data) > 0 and isinstance(existing_data[0], dict)
                    else None
                )
                if first_id is not None:
                    client.table("partner_manifests").update(payload).eq("id", first_id).execute()
                else:
                    client.table("partner_manifests").insert(payload).execute()
            return {
                "products_count": len(compliant),
                "manifest_type": body.manifest_type,
                "acp_validated": True,
                "acp_non_compliant_count": len(non_compliant),
            }

    return {"products_count": len(products), "manifest_type": body.manifest_type, "acp_validated": False}


@router.get("/embeddings/status")
async def get_embeddings_status() -> Dict[str, Any]:
    """
    Return embedding status for products and KB articles: counts with/without embedding,
    and whether the embedding API is configured. Used by admin UI to show status and trigger backfill.
    """
    embedding_configured = getattr(settings, "embedding_configured", False)
    client = get_supabase()
    products_total = products_with = products_without = 0
    kb_total = kb_with = kb_without = 0
    if client:
        try:
            r = client.table("products").select("id").is_("deleted_at", "null").limit(10000).execute()
            r_yes = client.table("products").select("id").is_("deleted_at", "null").not_.is_("embedding", "null").limit(10000).execute()
            products_total = len(r.data or [])
            products_with = len(r_yes.data or [])
            products_without = max(0, products_total - products_with)
        except Exception:
            pass
        try:
            r = client.table("partner_kb_articles").select("id").eq("is_active", True).limit(10000).execute()
            r_yes = client.table("partner_kb_articles").select("id").eq("is_active", True).not_.is_("embedding", "null").limit(10000).execute()
            kb_total = len(r.data or [])
            kb_with = len(r_yes.data or [])
            kb_without = max(0, kb_total - kb_with)
        except Exception:
            pass
    return {
        "embedding_configured": embedding_configured,
        "products": {"total": products_total, "with_embedding": products_with, "without_embedding": products_without},
        "kb_articles": {"total": kb_total, "with_embedding": kb_with, "without_embedding": kb_without},
    }


@router.post("/embeddings/backfill")
async def backfill_embeddings(
    product_id: Optional[str] = Query(None, description="Single product ID (products only)"),
    article_id: Optional[str] = Query(None, description="Single KB article ID (kb_articles only)"),
    limit: int = Query(500, ge=1, le=2000, description="Max records to backfill when no single id given"),
    type: str = Query("products", description="Backfill target: 'products' or 'kb_articles'"),
):
    """
    Backfill embeddings for products or partner KB articles.
    - type=products (default): product_id for one product, else all products missing embeddings (up to limit).
    - type=kb_articles: article_id for one article, else all KB articles missing embeddings (up to limit).
    Requires embedding provider (OpenAI or Azure) to be configured (EMBEDDING_* / OPENAI_API_KEY).
    """
    if type == "kb_articles":
        if article_id:
            ok = await backfill_kb_article_embedding(article_id)
            return {"article_id": article_id, "updated": ok}
        result = await backfill_all_kb_article_embeddings(limit=limit)
        return result
    # default: products
    if product_id:
        ok = await backfill_product_embedding(product_id)
        return {"product_id": product_id, "updated": ok}
    result = await backfill_all_product_embeddings(limit=limit)
    return result


# --- Module 2: Legacy Adapter Layer ---


class LegacyIngestColumnMap(BaseModel):
    """Optional column mapping override: legacy_header -> canonical_field."""

    column_map: Optional[Dict[str, str]] = None


@router.post("/legacy/ingest")
async def legacy_ingest(
    partner_id: str = Query(..., description="Partner ID that owns these products"),
    replace_legacy: bool = Query(False, description="Replace existing legacy products before insert"),
    column_map: Optional[str] = Query(None, description="JSON object of column mapping overrides"),
    file: UploadFile = File(..., description="CSV, Excel (.xlsx), or JSON file"),
):
    """
    Legacy Adapter: Ingest CSV, Excel, or JSON feed into products table.

    Maps legacy columns to canonical schema (name, description, price, image_url, etc.).
    Normalized products are indexed for Scout Engine discovery.

    Supports: Shopify export, WooCommerce CSV, generic CSV/Excel/JSON.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    cm: Optional[Dict[str, str]] = None
    if column_map:
        try:
            import json

            cm = json.loads(column_map)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid column_map JSON")

    filename = (file.filename or "").lower()
    products: List[Dict[str, Any]] = []

    if filename.endswith(".csv"):
        products = parse_csv_to_products(content, cm)
    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        try:
            products = parse_excel_to_products(content, cm)
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Excel support requires openpyxl. Add to requirements.txt: openpyxl>=3.0.0",
            )
    elif filename.endswith(".json"):
        products = parse_json_to_products(content, cm)
    else:
        # Try JSON first, then CSV
        try:
            products = parse_json_to_products(content, cm)
        except Exception:
            products = parse_csv_to_products(content, cm)

    if not products:
        return {
            "products_count": 0,
            "inserted": 0,
            "message": "No valid products found in file",
            "column_map": cm or DEFAULT_COLUMN_MAP,
        }

    result = await upsert_products_from_legacy(
        partner_id=partner_id,
        products=products,
        replace_legacy=replace_legacy,
    )

    return {
        "products_count": len(products),
        "inserted": result.get("inserted", 0),
        "updated": result.get("updated", 0),
        "error": result.get("error"),
        "preview": products[:3] if products else [],
    }


@router.get("/legacy/column-map")
async def legacy_column_map():
    """Return default column mapping for legacy formats."""
    return {"column_map": DEFAULT_COLUMN_MAP}


@router.put("/partners")
async def onboard_shopify_partner(body: ShopifyPartnerOnboardBody):
    """
    Onboard a curated Shopify partner. Creates/updates partner, internal_agent_registry,
    and shopify_curated_partners. Access token stored in Supabase Vault when access_token provided.
    """
    from db import get_supabase, onboard_shopify_curated_partner  # type: ignore[reportAttributeAccessIssue]

    if not body.shop_url or not body.mcp_endpoint:
        raise HTTPException(status_code=400, detail="shop_url and mcp_endpoint are required")

    result = await onboard_shopify_curated_partner(
        shop_url=body.shop_url.strip().lower().replace("https://", "").replace("http://", "").rstrip("/"),
        mcp_endpoint=body.mcp_endpoint.strip().rstrip("/"),
        display_name=body.display_name.strip() or body.shop_url,
        supported_capabilities=body.supported_capabilities or [],
        available_to_customize=body.available_to_customize,
        price_premium_percent=float(body.price_premium_percent) if body.price_premium_percent is not None else 0.0,
        access_token=body.access_token,
        access_token_vault_ref=body.access_token_vault_ref,
    )
    return result


@router.post("/ucp-partners")
async def onboard_ucp_partner_endpoint(body: UCPPartnerOnboardBody):
    """
    Onboard a UCP-only partner. Provide either manifest_json (paste UCP manifest) or base_url.
    display_name is optional; derived from manifest or base_url if omitted.
    """
    import json
    from db import onboard_ucp_partner as db_onboard_ucp, _base_url_from_manifest_json  # type: ignore[reportAttributeAccessIssue]

    base_url: Optional[str] = body.base_url and body.base_url.strip() or None
    display_name: Optional[str] = body.display_name and body.display_name.strip() or None

    if body.manifest_json and body.manifest_json.strip():
        try:
            manifest = json.loads(body.manifest_json.strip())
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid manifest JSON: {e}")
        derived = _base_url_from_manifest_json(manifest)
        if derived:
            base_url = base_url or derived
        if not display_name and isinstance(manifest, dict):
            display_name = (manifest.get("name") or manifest.get("display_name") or "").strip() or None
    if not base_url:
        raise HTTPException(status_code=400, detail="Provide either base_url or valid manifest_json with an endpoint")
    result = await db_onboard_ucp(
        base_url=base_url,
        display_name=display_name or base_url,
        price_premium_percent=float(body.price_premium_percent) if body.price_premium_percent is not None else 0.0,
        available_to_customize=body.available_to_customize,
        access_token=body.access_token,
        access_token_vault_ref=body.access_token_vault_ref,
    )
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/ucp-partners")
async def list_ucp_partners():
    """List UCP-only partners from internal_agent_registry (transport_type=UCP)."""
    from db import get_supabase

    client = get_supabase()
    if not client:
        return {"ucp_partners": []}
    try:
        result = (
            client.table("internal_agent_registry")
            .select("id, base_url, display_name, enabled, available_to_customize, price_premium_percent, access_token_vault_ref, created_at, updated_at")
            .eq("transport_type", "UCP")
            .order("display_name")
            .execute()
        )
        data = result.data if isinstance(result.data, list) else []
        for row in data:
            if isinstance(row, dict) and "access_token_vault_ref" in row:
                row["has_token"] = bool(row.get("access_token_vault_ref"))
        return {"ucp_partners": data}
    except Exception:
        return {"ucp_partners": []}


@router.get("/ucp-partners/status")
async def ucp_partners_status():
    """
    Diagnostic: how many UCP partner URLs Scout uses for discovery.
    Same source as get_internal_agent_urls() so you can verify Discovery sees your partners.
    """
    from db import get_internal_agent_urls  # type: ignore[reportAttributeAccessIssue]

    urls = await get_internal_agent_urls()
    # Mask for logs: show only scheme and host
    masked = []
    for u in urls:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(u)
            host = parsed.netloc or u.split("/")[2] if u.startswith("http") else "***"
            masked.append(f"{parsed.scheme or 'https'}://{host}")
        except Exception:
            masked.append("***")
    return {"ucp_partner_count": len(urls), "ucp_origins_masked": masked}


class UCPPartnerPatchBody(BaseModel):
    """Update UCP partner display_name, enabled, price_premium_percent, available_to_customize, optional access_token."""

    display_name: Optional[str] = None
    enabled: Optional[bool] = None
    price_premium_percent: Optional[float] = None
    available_to_customize: Optional[bool] = None
    access_token: Optional[str] = None


@router.patch("/ucp-partners/{registry_id}")
async def patch_ucp_partner(registry_id: str, body: UCPPartnerPatchBody):
    """Update a UCP partner's display_name, enabled, price_premium_percent, available_to_customize, or optional access_token."""
    from db import get_supabase
    from datetime import datetime, timezone
    import uuid as uuid_module

    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")
    updates: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.display_name is not None:
        updates["display_name"] = str(body.display_name).strip() or None
    if body.enabled is not None:
        updates["enabled"] = bool(body.enabled)
    if body.price_premium_percent is not None:
        updates["price_premium_percent"] = float(body.price_premium_percent)
    if body.available_to_customize is not None:
        updates["available_to_customize"] = bool(body.available_to_customize)

    if body.access_token is not None:
        try:
            row = (
                client.table("internal_agent_registry")
                .select("base_url")
                .eq("id", registry_id)
                .eq("transport_type", "UCP")
                .limit(1)
                .execute()
            )
            data = row.data if isinstance(row.data, list) else []
            first = data[0] if data else {}
            base_url = str(first.get("base_url", "")) if isinstance(first, dict) else ""
            secret_name = f"ucp_{base_url.replace('https://', '').replace('http://', '').replace('/', '_')}_{uuid_module.uuid4().hex[:8]}"
            r = client.rpc("insert_shopify_token", {"secret_name": secret_name, "secret_value": body.access_token}).execute()
            if r.data is not None:
                vault_ref = str(r.data) if not isinstance(r.data, dict) else str(r.data.get("id", r.data))
                updates["access_token_vault_ref"] = vault_ref
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to store token: {e}")

    if len(updates) <= 1:
        return {"id": registry_id, "updated": False}
    try:
        client.table("internal_agent_registry").update(updates).eq("id", registry_id).eq(
            "transport_type", "UCP"
        ).execute()
        return {"id": registry_id, "updated": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
