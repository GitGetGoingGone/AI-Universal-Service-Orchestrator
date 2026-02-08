"""Product and bundle API - proxies to Discovery service."""

from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from clients import (
    get_product_details,
    get_bundle_details,
    add_to_bundle as add_to_bundle_client,
    remove_from_bundle as remove_from_bundle_client,
    proceed_to_checkout as proceed_to_checkout_client,
    create_payment_intent as create_payment_intent_client,
    create_change_request as create_change_request_client,
)

router = APIRouter(prefix="/api/v1", tags=["Products"])


@router.get("/products/{product_id}")
async def get_product(product_id: str):
    """Get product by ID. For View Details action."""
    try:
        return await get_product_details(product_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Product not found")
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")


@router.get("/bundles/{bundle_id}")
async def get_bundle(bundle_id: str):
    """Get bundle by ID. For View Bundle action."""
    try:
        return await get_bundle_details(bundle_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Bundle not found")
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")


class AddToBundleBody(BaseModel):
    """Request body for adding a product to a bundle."""

    product_id: str
    user_id: Optional[str] = None
    bundle_id: Optional[str] = None


@router.post("/bundle/add")
async def add_to_bundle(body: AddToBundleBody):
    """Add product to bundle. For Add to Bundle action."""
    try:
        return await add_to_bundle_client(
            product_id=body.product_id,
            user_id=body.user_id,
            bundle_id=body.bundle_id,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Product not found")
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")


class RemoveFromBundleBody(BaseModel):
    """Request body for removing an item from a bundle."""

    item_id: str  # bundle_leg id from bundle card


@router.post("/bundle/remove")
async def remove_from_bundle(body: RemoveFromBundleBody):
    """Remove item from bundle. For Remove action on bundle card."""
    try:
        return await remove_from_bundle_client(item_id=body.item_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Item or bundle not found")
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")


class CheckoutBody(BaseModel):
    """Request body for proceeding to checkout."""

    bundle_id: str


@router.post("/checkout")
async def proceed_to_checkout(body: CheckoutBody):
    """Proceed to checkout with bundle. Creates order, returns order_id for payment."""
    try:
        return await proceed_to_checkout_client(bundle_id=body.bundle_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Bundle not found")
        if e.response.status_code == 400:
            raise HTTPException(status_code=400, detail="Bundle is empty; add items before checkout")
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")


class CreatePaymentBody(BaseModel):
    """Request body for creating payment intent."""

    order_id: str


@router.post("/payment/create")
async def create_payment(body: CreatePaymentBody):
    """Create Stripe PaymentIntent for order. Use order_id from checkout response."""
    try:
        return await create_payment_intent_client(order_id=body.order_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Order not found")
        if e.response.status_code == 400:
            raise HTTPException(status_code=400, detail=str(e.response.json().get("detail", "Bad request")))
        raise HTTPException(status_code=502, detail=f"Payment service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment service error: {e}")


class CreateChangeRequestBody(BaseModel):
    """Request body for creating change request."""

    order_id: str
    order_leg_id: str
    partner_id: str
    original_item: Dict[str, Any]
    requested_change: Dict[str, Any]
    respond_by: Optional[str] = None


@router.post("/change-request")
async def create_change_request(body: CreateChangeRequestBody):
    """Create change request and notify partner. For Request Change action."""
    try:
        return await create_change_request_client(
            order_id=body.order_id,
            order_leg_id=body.order_leg_id,
            partner_id=body.partner_id,
            original_item=body.original_item,
            requested_change=body.requested_change,
            respond_by=body.respond_by,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            raise HTTPException(status_code=400, detail=str(e.response.json().get("detail", "Bad request")))
        raise HTTPException(status_code=502, detail=f"Omnichannel Broker error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Omnichannel Broker error: {e}")
