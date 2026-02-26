"""Stripe webhook handler - payment_intent.succeeded/failed."""

import json
import logging

import stripe
from fastapi import APIRouter, HTTPException, Request, Response

from config import settings
from db import (
    create_product_sponsorship,
    update_payment_status,
    update_order_payment_status,
)

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
        meta = pi.metadata or {}

        if meta.get("type") == "sponsorship":
            product_id = meta.get("product_id")
            partner_id = meta.get("partner_id")
            start_at = meta.get("start_at")
            end_at = meta.get("end_at")
            amount_cents = int(meta.get("amount_cents", 0))
            if product_id and partner_id and start_at and end_at and amount_cents:
                row = await create_product_sponsorship(
                    product_id=product_id,
                    partner_id=partner_id,
                    start_at=start_at,
                    end_at=end_at,
                    amount_cents=amount_cents,
                    currency="USD",
                    stripe_payment_intent_id=pi.id,
                )
                if row:
                    logger.info("Sponsorship created for product %s", product_id)
            else:
                logger.warning("Sponsorship metadata incomplete: %s", meta)
        else:
            order_id = meta.get("order_id")
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
    elif event.type == "checkout.session.completed":
        session = event.data.object
        order_id = (session.metadata or {}).get("order_id")
        if order_id:
            await update_order_payment_status(order_id, "paid")
            logger.info("Checkout completed for order %s", order_id)

    return Response(status_code=200)
