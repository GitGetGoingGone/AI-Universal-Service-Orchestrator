"""Admin endpoints for Module 1: manifest ingest, embedding backfill; Module 2: Legacy Adapter."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from db import upsert_products_from_legacy
from manifest_cache import cache_partner_manifest
from semantic_search import backfill_product_embedding, backfill_all_product_embeddings

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

        compliant, non_compliant = filter_acp_compliant_products(products, strict=True)
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
                if existing.data:
                    client.table("partner_manifests").update(payload).eq("id", existing.data[0]["id"]).execute()
                else:
                    client.table("partner_manifests").insert(payload).execute()
            return {
                "products_count": len(compliant),
                "manifest_type": body.manifest_type,
                "acp_validated": True,
                "acp_non_compliant_count": len(non_compliant),
            }

    return {"products_count": len(products), "manifest_type": body.manifest_type, "acp_validated": False}


@router.post("/embeddings/backfill")
async def backfill_embeddings(
    product_id: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000, description="Max products to backfill when product_id omitted"),
):
    """
    Backfill embedding for a product (or all products missing embeddings when product_id omitted).
    Requires embedding provider (OpenAI or Azure) to be configured (EMBEDDING_* / OPENAI_API_KEY).
    """
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
