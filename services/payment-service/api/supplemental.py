"""Supplemental charges and refunds for post-order design (AERD)."""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db import create_payment_record
from stripe_adapter import create_supplemental_payment_intent, create_refund

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Supplemental"])


class SupplementalChargeBody(BaseModel):
    """Create supplemental PaymentIntent for design add/edit."""

    experience_session_id: str
    order_id: str = Field(..., description="Original order ID for payment record")
    leg_id: str
    amount_cents: int = Field(..., description="Amount in cents")
    currency: str = "usd"
    description: str = Field("", description="Line item description")


@router.post("/payment/supplemental")
async def create_supplemental_charge(body: SupplementalChargeBody):
    """Create supplemental Stripe PaymentIntent for design add/edit (AERD)."""
    if body.amount_cents < 50:
        raise HTTPException(status_code=400, detail="Amount too small")

    try:
        result = await create_supplemental_payment_intent(
            experience_session_id=body.experience_session_id,
            leg_id=body.leg_id,
            amount_cents=body.amount_cents,
            currency=body.currency,
            description=body.description,
        )
        await create_payment_record(
            order_id=body.order_id,
            amount=body.amount_cents / 100.0,
            currency=body.currency.upper(),
            stripe_payment_intent_id=result["payment_intent_id"],
            status="pending",
            experience_session_id=body.experience_session_id,
            payment_type="supplemental",
        )
        return {
            "client_secret": result["client_secret"],
            "payment_intent_id": result["payment_intent_id"],
            "amount": body.amount_cents / 100.0,
            "currency": body.currency,
        }
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


class RefundBody(BaseModel):
    """Request partial refund for leg (AERD Replace/Delete)."""

    payment_intent_id: str = Field(..., description="Original PaymentIntent ID")
    amount_cents: int = Field(..., description="Amount to refund in cents")
    reason: str = Field("requested_by_customer", description="Stripe refund reason")


@router.post("/payment/refund")
async def create_refund_route(body: RefundBody):
    """Create Stripe refund for partial amount (AERD Replace/Delete)."""
    if body.amount_cents < 50:
        raise HTTPException(status_code=400, detail="Refund amount too small")

    try:
        result = await create_refund(
            payment_intent_id=body.payment_intent_id,
            amount_cents=body.amount_cents,
            reason=body.reason,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
