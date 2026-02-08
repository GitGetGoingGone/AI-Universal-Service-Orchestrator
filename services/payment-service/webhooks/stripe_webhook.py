"""Stripe webhook handler - payment_intent.succeeded/failed."""

import json
import logging

import stripe
from fastapi import APIRouter, HTTPException, Request, Response

from config import settings
from db import update_payment_status, update_order_payment_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks (payment_intent.succeeded, payment_intent.payment_failed).
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    if not settings.stripe_webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured, skipping verification")
        stripe.api_key = settings.stripe_secret_key
        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
        except stripe.SignatureVerificationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")

    if event.type == "payment_intent.succeeded":
        pi = event.data.object
        order_id = (pi.metadata or {}).get("order_id")
        if order_id:
            charge_id = getattr(pi, "latest_charge", None)
            await update_payment_status(pi.id, "succeeded", transaction_id=charge_id)
            await update_order_payment_status(order_id, "paid")
            logger.info("Payment succeeded for order %s", order_id)
    elif event.type == "payment_intent.payment_failed":
        pi = event.data.object
        order_id = (pi.metadata or {}).get("order_id")
        await update_payment_status(pi.id, "failed")
        if order_id:
            await update_order_payment_status(order_id, "failed")
        logger.warning("Payment failed for order %s", order_id)

    return Response(status_code=200)
