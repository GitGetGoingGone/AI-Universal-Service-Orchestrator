"""Sponsorship API - create PaymentIntent for product sponsorship."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import get_platform_config_sponsorship, get_product_partner
from stripe_adapter import create_sponsorship_payment_intent

router = APIRouter(prefix="/api/v1", tags=["Sponsorship"])


class CreateSponsorshipBody(BaseModel):
    """Create sponsorship payment intent."""

    product_id: str
    partner_id: str
    duration_days: int


@router.post("/sponsorship/create")
async def create_sponsorship(body: CreateSponsorshipBody):
    """
    Create Stripe PaymentIntent for product sponsorship.
    Validates product belongs to partner, computes amount from platform_config.
    Returns client_secret for frontend to confirm payment.
    """
    if body.duration_days < 1 or body.duration_days > 365:
        raise HTTPException(status_code=400, detail="duration_days must be 1-365")

    product = await get_product_partner(body.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if str(product.get("partner_id", "")) != str(body.partner_id):
        raise HTTPException(status_code=403, detail="Product does not belong to partner")

    config = await get_platform_config_sponsorship()
    if not config or not config.get("sponsorship_enabled", True):
        raise HTTPException(status_code=400, detail="Sponsorship is disabled")

    price_per_day = int(config.get("product_price_per_day_cents", 1000))
    amount_cents = price_per_day * body.duration_days
    if amount_cents < 50:
        raise HTTPException(status_code=400, detail="Amount too small (min $0.50)")

    now = datetime.now(timezone.utc)
    start_at = now.isoformat()
    end_at = (now + timedelta(days=body.duration_days)).isoformat()

    try:
        result = await create_sponsorship_payment_intent(
            product_id=body.product_id,
            partner_id=body.partner_id,
            amount_cents=amount_cents,
            start_at=start_at,
            end_at=end_at,
            currency="usd",
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "client_secret": result["client_secret"],
        "payment_intent_id": result["payment_intent_id"],
        "amount_cents": amount_cents,
        "amount": amount_cents / 100,
        "currency": "USD",
        "start_at": start_at,
        "end_at": end_at,
        "duration_days": body.duration_days,
    }
