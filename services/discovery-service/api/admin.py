"""Admin endpoints for Module 1: manifest ingest, embedding backfill."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from manifest_cache import cache_partner_manifest
from semantic_search import backfill_product_embedding

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
async def backfill_embeddings(product_id: Optional[str] = Query(None)):
    """
    Backfill embedding for a product (or all products when product_id omitted).
    Requires Azure OpenAI embedding deployment.
    """
    if product_id:
        ok = await backfill_product_embedding(product_id)
        return {"product_id": product_id, "updated": ok}
    # TODO: batch backfill when product_id omitted
    return {"message": "Specify product_id for single backfill; batch coming soon"}
