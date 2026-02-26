"""Payment checkout API - create PaymentIntent for order."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from db import get_order_with_items, create_payment_record, update_order_payment_status
from stripe_adapter import create_payment_intent, create_checkout_session

router = APIRouter(prefix="/api/v1", tags=["Payment"])


class CreatePaymentBody(BaseModel):
    """Create payment intent for order."""

    order_id: str


@router.post("/payment/create")
async def create_payment(body: CreatePaymentBody):
    """
    Create Stripe PaymentIntent for order.
    Returns client_secret for frontend to confirm payment.
    """
    order = await get_order_with_items(body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Order already paid")

    total = float(order.get("total_amount", 0))
    currency = order.get("currency", "USD")
    amount_cents = int(round(total * 100))
    if amount_cents < 50:  # Stripe minimum
        raise HTTPException(status_code=400, detail="Amount too small")

    try:
        result = await create_payment_intent(
            order_id=body.order_id,
            amount_cents=amount_cents,
            currency=currency.lower(),
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    await create_payment_record(
        order_id=body.order_id,
        amount=total,
        currency=currency,
        stripe_payment_intent_id=result["payment_intent_id"],
        status="pending",
    )

    return {
        "order_id": body.order_id,
        "client_secret": result["client_secret"],
        "payment_intent_id": result["payment_intent_id"],
        "amount": total,
        "currency": currency,
    }


class CheckoutSessionBody(BaseModel):
    """Create Checkout Session for redirect payment."""

    order_id: str
    success_url: str
    cancel_url: str


@router.post("/payment/checkout-session")
async def create_checkout_session_route(body: CheckoutSessionBody):
    """
    Create Stripe Checkout Session. Returns url for redirect.
    No client-side Stripe.js needed.
    """
    order = await get_order_with_items(body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Order already paid")

    items = order.get("items") or []
    line_items = []
    for item in items:
        unit = float(item.get("unit_price") or 0)
        qty = int(item.get("quantity") or 1)
        line_items.append({
            "price_data": {
                "currency": order.get("currency", "usd").lower(),
                "product_data": {"name": item.get("item_name") or "Item"},
                "unit_amount": int(round(unit * 100)),
            },
            "quantity": qty,
        })
    if not line_items:
        total = float(order.get("total_amount") or 0)
        line_items = [{
            "price_data": {
                "currency": order.get("currency", "usd").lower(),
                "product_data": {"name": order.get("bundle_id", "Order")},
                "unit_amount": max(50, int(round(total * 100))),
            },
            "quantity": 1,
        }]

    try:
        result = await create_checkout_session(
            order_id=body.order_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            line_items=line_items,
            currency=order.get("currency", "usd").lower(),
        )
        return {"url": result["url"], "session_id": result.get("session_id")}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


class CheckoutSessionFromOrderBody(BaseModel):
    """Create Checkout Session with order data (when order is in Discovery DB only)."""

    order_id: str
    success_url: str
    cancel_url: str
    order: dict  # { items: [...], total_amount, currency }


@router.post("/payment/checkout-session-from-order")
async def create_checkout_session_from_order_route(body: CheckoutSessionFromOrderBody):
    """
    Create Stripe Checkout Session using provided order data.
    Use when order exists in Discovery but not in Payment service DB.
    """
    order = body.order
    items = order.get("items") or []
    line_items = []
    for item in items:
        unit = float(item.get("unit_price") or 0)
        qty = int(item.get("quantity") or 1)
        line_items.append({
            "price_data": {
                "currency": (order.get("currency") or "usd").lower(),
                "product_data": {"name": item.get("item_name") or "Item"},
                "unit_amount": int(round(unit * 100)),
            },
            "quantity": qty,
        })
    if not line_items:
        total = float(order.get("total_amount") or 0)
        line_items = [{
            "price_data": {
                "currency": (order.get("currency") or "usd").lower(),
                "product_data": {"name": order.get("bundle_id", "Order")},
                "unit_amount": max(50, int(round(total * 100))),
            },
            "quantity": 1,
        }]

    try:
        result = await create_checkout_session(
            order_id=body.order_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            line_items=line_items,
            currency=(order.get("currency") or "usd").lower(),
        )
        return {"url": result["url"], "session_id": result.get("session_id")}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


class ConfirmPaymentBody(BaseModel):
    """Confirm payment for order (demo mode only)."""

    order_id: str


@router.post("/payment/confirm")
async def confirm_payment(body: ConfirmPaymentBody):
    """
    Mark order as paid (demo/testing only).
    Use when DEMO_PAYMENT=true. Simulates payment success for ChatGPT flow.
    In production, payment is completed via Stripe checkout + webhook.
    """
    if not settings.demo_payment:
        raise HTTPException(
            status_code=403,
            detail="confirmPayment is disabled. Set DEMO_PAYMENT=true for testing.",
        )
    order = await get_order_with_items(body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Order already paid")

    ok = await update_order_payment_status(body.order_id, "paid")
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update order")

    return {
        "order_id": body.order_id,
        "status": "paid",
        "message": "Payment confirmed (demo mode). Order is now paid.",
    }
