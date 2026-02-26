"""Product and bundle API - proxies to Discovery service."""

from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from clients import (
    get_product_details,
    get_bundle_details,
    add_to_bundle as add_to_bundle_client,
    add_to_bundle_bulk as add_to_bundle_bulk_client,
    remove_from_bundle as remove_from_bundle_client,
    replace_in_bundle as replace_in_bundle_client,
    proceed_to_checkout as proceed_to_checkout_client,
    create_payment_intent as create_payment_intent_client,
    confirm_payment as confirm_payment_client,
    create_checkout_session as create_checkout_session_client,
    create_checkout_session_from_order as create_checkout_session_from_order_client,
    get_order_status as get_order_status_client,
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


class AddBulkBody(BaseModel):
    """Request body for adding multiple products to a bundle."""

    product_ids: list[str]
    user_id: Optional[str] = None
    bundle_id: Optional[str] = None
    pickup_time: Optional[str] = None
    pickup_address: Optional[str] = None
    delivery_address: Optional[str] = None
    requires_fulfillment: Optional[bool] = None  # When true, fulfillment_fields (or default 3) are required
    fulfillment_fields: Optional[list[str]] = None  # Dynamic required fields per bundle (e.g. ["delivery_address"])


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


@router.post("/bundle/add-bulk")
async def add_to_bundle_bulk(body: AddBulkBody):
    """Add multiple products to bundle. For Add curated bundle action."""
    if body.requires_fulfillment:
        required = body.fulfillment_fields or ["pickup_time", "pickup_address", "delivery_address"]
        missing = []
        for f in required:
            val = getattr(body, f, None)
            if not (val or "").strip():
                missing.append(f)
        if missing:
            field_labels = {"pickup_time": "pickup time", "pickup_address": "pickup address", "delivery_address": "delivery address"}
            labels = [field_labels.get(f, f) for f in missing]
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "fulfillment_details_required",
                    "required_fields": missing,
                    "message": f"Please provide {', '.join(labels)} before adding this bundle.",
                },
            )
    try:
        return await add_to_bundle_bulk_client(
            product_ids=body.product_ids,
            user_id=body.user_id,
            bundle_id=body.bundle_id,
            pickup_time=body.pickup_time,
            pickup_address=body.pickup_address,
            delivery_address=body.delivery_address,
            fulfillment_fields=body.fulfillment_fields,
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


class ReplaceInBundleBody(BaseModel):
    """Request body for replacing a product in bundle (category refinement)."""

    bundle_id: str
    leg_id: str
    new_product_id: str


@router.post("/bundle/replace")
async def replace_in_bundle(body: ReplaceInBundleBody):
    """Replace a product in bundle (category refinement)."""
    try:
        return await replace_in_bundle_client(
            bundle_id=body.bundle_id,
            leg_id=body.leg_id,
            new_product_id=body.new_product_id,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Bundle or product not found")
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Discovery service error: {e}")


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


class ConfirmPaymentBody(BaseModel):
    """Request body for confirming payment (demo mode)."""

    order_id: str


class CheckoutSessionBody(BaseModel):
    """Create Checkout Session for redirect payment."""

    order_id: str
    success_url: str
    cancel_url: str


@router.post("/payment/checkout-session")
async def create_checkout_session_route(body: CheckoutSessionBody):
    """Create Stripe Checkout Session. Returns url for redirect (no Stripe.js needed)."""
    try:
        return await create_checkout_session_client(
            order_id=body.order_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            order = await get_order_status_client(body.order_id)
            if order and "error" not in order:
                return await create_checkout_session_from_order_client(
                    order_id=body.order_id,
                    success_url=body.success_url,
                    cancel_url=body.cancel_url,
                    order=order,
                )
            raise HTTPException(status_code=404, detail="Order not found")
        if e.response.status_code == 400:
            raise HTTPException(status_code=400, detail=str(e.response.json().get("detail", "Bad request")))
        raise HTTPException(status_code=502, detail=f"Payment service error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment service error: {e}")


@router.post("/payment/confirm")
async def confirm_payment(body: ConfirmPaymentBody):
    """Confirm payment for order (demo mode). Marks order as paid. Requires DEMO_PAYMENT=true."""
    try:
        return await confirm_payment_client(order_id=body.order_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Order not found")
        if e.response.status_code == 400:
            raise HTTPException(status_code=400, detail=str(e.response.json().get("detail", "Bad request")))
        if e.response.status_code == 403:
            raise HTTPException(status_code=403, detail=str(e.response.json().get("detail", "Demo mode disabled")))
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
