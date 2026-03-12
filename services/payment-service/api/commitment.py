"""Commitment precheck API - vendor-agnostic tax/shipping TCO before Gateway charge."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db import get_bundle_for_precheck, get_partner_vendor_type
from packages.shared.commitment import get_provider
from packages.shared.schemas import StandardizedShipping

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Commitment"])


class CommitmentPrecheckBody(BaseModel):
    """Request for commitment precheck."""

    bundle_id: str = Field(..., description="Bundle ID from Discovery")
    shipping: StandardizedShipping = Field(..., description="StandardizedShipping for tax/shipping")
    thread_id: str | None = None
    user_id: str | None = None


@router.post("/commitment/precheck")
async def commitment_precheck(body: CommitmentPrecheckBody):
    """
    Vendor-agnostic commitment precheck: create drafts/reservations per partner,
    return TCO (total_amount, currency, breakdown). Use before creating PaymentIntent.
    """
    bundle_data = await get_bundle_for_precheck(body.bundle_id)
    if not bundle_data:
        raise HTTPException(status_code=404, detail="Bundle not found")

    legs_by_partner = bundle_data.get("legs_by_partner", {})
    if not legs_by_partner:
        raise HTTPException(status_code=400, detail="Bundle has no items")

    shipping_addr = body.shipping.to_shopify_shipping_address()
    total_amount = 0.0
    currency = bundle_data.get("currency", "USD")
    breakdown: Dict[str, Any] = {}

    for partner_id, items in legs_by_partner.items():
        vendor_type = get_partner_vendor_type(partner_id)
        provider = get_provider(vendor_type)
        if not provider:
            provider = get_provider("local")
        if not provider:
            raise HTTPException(
                status_code=503,
                detail=f"No commitment provider for vendor_type={vendor_type}",
            )

        line_items = [
            {
                "title": it.get("item_name", "Item"),
                "price": it.get("price", "0"),
                "quantity": it.get("quantity", 1),
                "taxable": True,
            }
            for it in items
        ]

        try:
            result = await provider.precheck(
                partner_id=partner_id,
                line_items=line_items,
                shipping_address=shipping_addr,
                email=body.shipping.email,
                name=body.shipping.name,
                phone=body.shipping.phone,
            )
        except Exception as e:
            logger.exception("Precheck failed for partner %s", partner_id)
            raise HTTPException(status_code=502, detail=str(e))

        total_amount += result.total_price + result.total_tax + result.total_shipping
        breakdown[partner_id] = {
            "vendor_type": vendor_type,
            "reservation_id": result.reservation_id,
            "total_price": result.total_price,
            "total_tax": result.total_tax,
            "total_shipping": result.total_shipping,
            "currency": result.currency,
        }

    return {
        "total_amount": round(total_amount, 2),
        "currency": currency,
        "breakdown": breakdown,
        "precheck_id": f"precheck-{body.bundle_id}",
    }


class CommitmentCancelBody(BaseModel):
    """Request to cancel external order (AERD Replace/Delete, re-sourcing)."""

    partner_id: str
    external_order_id: str
    vendor_type: str = "shopify"


@router.post("/commitment/cancel")
async def commitment_cancel(body: CommitmentCancelBody):
    """Cancel external order at vendor (Shopify cancel, etc.). Used by AERD and re-sourcing."""
    provider = get_provider(body.vendor_type) or get_provider("local")
    if not provider:
        raise HTTPException(status_code=503, detail=f"No provider for vendor_type={body.vendor_type}")
    try:
        ok = await provider.cancel(
            partner_id=body.partner_id,
            external_order_id=body.external_order_id,
        )
        return {"ok": ok}
    except Exception as e:
        logger.exception("Commitment cancel failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
