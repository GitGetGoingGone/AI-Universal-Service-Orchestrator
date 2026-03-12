"""Stripe webhook handler - payment_intent.succeeded/failed."""

import json
import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, HTTPException, Request, Response

from config import settings
from db import (
    create_product_sponsorship,
    update_payment_status,
    update_order_payment_status,
    get_experience_session_legs_by_thread,
    update_experience_session_leg_external_order,
    update_order_leg_external_order,
    transition_legs_to_in_customization,
)
from packages.shared.commitment import get_provider
from db import get_supabase

logger = logging.getLogger(__name__)


async def _link_order_to_session(thread_id: str, order_id: str) -> None:
    """Link order_id to experience_session for SLA/re-sourcing."""
    client = get_supabase()
    if not client:
        return
    try:
        client.table("experience_sessions").update({
            "order_id": order_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("thread_id", thread_id).execute()
    except Exception as e:
        logger.warning("Failed to link order to session: %s", e)

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

                # Commitment flow: complete drafts per vendor, update legs
                if meta.get("commitment_flow") == "1":
                    thread_id = meta.get("thread_id")
                    breakdown_str = meta.get("commitment_breakdown")
                    if thread_id and breakdown_str:
                        try:
                            breakdown = json.loads(breakdown_str)
                            legs = await get_experience_session_legs_by_thread(thread_id)
                            for partner_id, precheck_data in breakdown.items():
                                if not isinstance(precheck_data, dict):
                                    continue
                                reservation_id = precheck_data.get("reservation_id")
                                vendor_type = precheck_data.get("vendor_type", "local")
                                if not reservation_id:
                                    continue
                                provider = get_provider(vendor_type) or get_provider("local")
                                if not provider:
                                    logger.warning("No provider for vendor_type=%s", vendor_type)
                                    continue
                                try:
                                    result = await provider.complete(
                                        partner_id=partner_id,
                                        reservation_id=reservation_id,
                                        payment_pending=False,
                                    )
                                    for leg in legs:
                                        if str(leg.get("partner_id")) == str(partner_id):
                                            await update_experience_session_leg_external_order(
                                                leg["id"],
                                                result.external_order_id,
                                                reservation_id,
                                                vendor_type,
                                            )
                                    await update_order_leg_external_order(
                                        order_id, partner_id,
                                        result.external_order_id,
                                        reservation_id,
                                        vendor_type,
                                    )
                                    logger.info(
                                        "Commitment complete partner=%s external_order=%s",
                                        partner_id, result.external_order_id,
                                    )
                                except Exception as e:
                                    logger.exception(
                                        "Commitment complete failed partner=%s: %s",
                                        partner_id, e,
                                    )

                        except json.JSONDecodeError as e:
                            logger.warning("Invalid commitment_breakdown JSON: %s", e)

                        if thread_id:
                            n = await transition_legs_to_in_customization(thread_id)
                            if n > 0:
                                logger.info("Transitioned %d legs to in_customization for thread %s", n, thread_id)
                            await _link_order_to_session(thread_id, order_id)

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
