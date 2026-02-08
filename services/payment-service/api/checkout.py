"""Payment checkout API - create PaymentIntent for order."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_order_with_items, create_payment_record
from stripe_adapter import create_payment_intent

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
