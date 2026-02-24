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
