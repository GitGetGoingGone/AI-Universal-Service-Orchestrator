"""ACP feed export and push API for ChatGPT/Gemini discovery."""

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from db import get_products_for_acp_export, get_partner_by_id, update_partner_last_acp_push, update_products_last_acp_push
from protocols.acp_compliance import filter_acp_compliant_products

router = APIRouter(prefix="/api/v1/feeds", tags=["Feeds"])

ACP_PUSH_THROTTLE_MINUTES = 15


def _product_to_acp_row(product: Dict[str, Any]) -> Dict[str, Any]:
    """Build one ACP feed row from product (with partner seller fields already merged)."""
    price = float(product.get("price", 0))
    currency = product.get("currency", "USD") or "USD"
    availability = product.get("availability")
    if availability is None or availability == "":
        is_avail = product.get("is_available", True)
        availability = "in_stock" if is_avail else "out_of_stock"
    target_countries = product.get("target_countries")
    if target_countries is None:
        target_countries = []
    if isinstance(target_countries, str):
        target_countries = [target_countries] if target_countries else []
    row = {
        "item_id": str(product.get("id", "")),
        "title": (product.get("name") or "")[:150],
        "description": (product.get("description") or "")[:5000],
        "url": product.get("url") or "",
        "image_url": product.get("image_url") or "",
        "price": f"{price:.2f} {currency}",
        "availability": availability,
        "brand": (product.get("brand") or "")[:70],
        "is_eligible_search": bool(product.get("is_eligible_search", True)),
        "is_eligible_checkout": bool(product.get("is_eligible_checkout", False)),
        "seller_name": (product.get("seller_name") or "")[:70],
        "seller_url": product.get("seller_url") or "",
        "return_policy": product.get("return_policy") or "",
        "target_countries": target_countries,
        "store_country": product.get("store_country") or "",
    }
    if row.get("is_eligible_checkout"):
        row["seller_privacy_policy"] = product.get("seller_privacy_policy") or ""
        row["seller_tos"] = product.get("seller_tos") or ""
    return row


async def _build_acp_rows(
    partner_id: Optional[str] = None,
    product_id: Optional[str] = None,
    product_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Load products with partner join, build ACP rows, filter to compliant only."""
    products = await get_products_for_acp_export(
        partner_id=partner_id, product_id=product_id, product_ids=product_ids
    )
    rows = [_product_to_acp_row(p) for p in products]
    require_checkout = any(r.get("is_eligible_checkout") for r in rows)
    compliant, _ = filter_acp_compliant_products(rows, require_checkout_fields=require_checkout, strict=True)
    return compliant


@router.get("/acp")
async def get_acp_feed(
    partner_id: Optional[str] = Query(None, description="Filter by partner"),
):
    """
    Public ACP feed URL for OpenAI (ChatGPT). Returns JSON Lines (one JSON object per line).
    Optional partner_id to get only that partner's products.
    """
    rows = await _build_acp_rows(partner_id=partner_id)
    body = "\n".join(json.dumps(r) for r in rows)
    return Response(
        content=body,
        media_type="application/x-ndjson",
    )


@router.get("/push-status")
async def push_status(
    partner_id: str = Query(..., description="Partner ID"),
):
    """Return next allowed ACP push time (15-minute throttle). Used by portal for countdown."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    last = partner.get("last_acp_push_at")
    if not last:
        return {"next_acp_push_allowed_at": None}
    if isinstance(last, str):
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        except ValueError:
            return {"next_acp_push_allowed_at": None}
    else:
        last_dt = last
    next_allowed = last_dt + timedelta(minutes=ACP_PUSH_THROTTLE_MINUTES)
    now = datetime.now(timezone.utc)
    if next_allowed.tzinfo is None:
        next_allowed = next_allowed.replace(tzinfo=timezone.utc)
    if now >= next_allowed:
        return {"next_acp_push_allowed_at": None}
    return {"next_acp_push_allowed_at": next_allowed.isoformat()}


class PushBody(BaseModel):
    scope: str  # "single" | "all" | "selected"
    product_id: Optional[str] = None
    product_ids: Optional[List[str]] = None  # required when scope=selected
    targets: List[str]  # ["chatgpt"] | ["gemini"] | ["chatgpt", "gemini"]
    partner_id: str


@router.post("/push")
async def push_feed(body: PushBody):
    """
    Push catalog to ChatGPT and/or Gemini.
    scope: single (one product) | all (full catalog) | selected (product_ids list).
    product_id: required when scope=single.
    product_ids: required when scope=selected.
    targets: chatgpt and/or gemini.
    ChatGPT: 15-minute throttle per partner; generates ACP feed and updates last_acp_push_at.
    Gemini: runs UCP validation and returns summary (no rate limit).
    """
    if body.scope not in ("single", "all", "selected"):
        raise HTTPException(status_code=400, detail="scope must be 'single', 'all', or 'selected'")
    if body.scope == "single" and not body.product_id:
        raise HTTPException(status_code=400, detail="product_id required when scope is 'single'")
    if body.scope == "selected":
        if not body.product_ids or not isinstance(body.product_ids, list):
            raise HTTPException(status_code=400, detail="product_ids (array) required when scope is 'selected'")
    if not body.targets:
        raise HTTPException(status_code=400, detail="targets required")
    valid_targets = {"chatgpt", "gemini"}
    for t in body.targets:
        if t.lower() not in valid_targets:
            raise HTTPException(status_code=400, detail=f"Invalid target: {t}")
    partner_id = body.partner_id
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    result: Dict[str, Any] = {}

    if "chatgpt" in [t.lower() for t in body.targets]:
        last = partner.get("last_acp_push_at")
        now = datetime.now(timezone.utc)
        if last:
            if isinstance(last, str):
                try:
                    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                except ValueError:
                    last_dt = now - timedelta(hours=1)
            else:
                last_dt = last
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            next_allowed = last_dt + timedelta(minutes=ACP_PUSH_THROTTLE_MINUTES)
            if now < next_allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limited",
                        "message": "Catalog can be updated again at {}".format(next_allowed.isoformat()),
                        "next_allowed_at": next_allowed.isoformat(),
                    },
                )
        rows = await _build_acp_rows(
            partner_id=partner_id,
            product_id=body.product_id if body.scope == "single" else None,
            product_ids=body.product_ids if body.scope == "selected" else None,
        )
        await update_partner_last_acp_push(partner_id)
        pushed_product_ids = (
            [body.product_id] if body.scope == "single" and body.product_id
            else body.product_ids if body.scope == "selected"
            else [r.get("item_id") for r in rows if r.get("item_id")]
        )
        if pushed_product_ids:
            await update_products_last_acp_push(pushed_product_ids, success=True)
        next_allowed = now + timedelta(minutes=ACP_PUSH_THROTTLE_MINUTES)
        result["chatgpt"] = "pushed"
        result["next_acp_push_allowed_at"] = next_allowed.isoformat()
        result["rows_pushed"] = len(rows)

    if "gemini" in [t.lower() for t in body.targets]:
        from protocols.ucp_compliance import validate_product_ucp
        products = await get_products_for_acp_export(
            partner_id=partner_id,
            product_id=body.product_id if body.scope == "single" else None,
            product_ids=body.product_ids if body.scope == "selected" else None,
        )
        compliant = 0
        non_compliant = 0
        for p in products:
            ok, _, _ = validate_product_ucp(p)
            if ok:
                compliant += 1
            else:
                non_compliant += 1
        result["gemini"] = "validated"
        result["ucp_compliant"] = compliant
        result["ucp_non_compliant"] = non_compliant

    return result
