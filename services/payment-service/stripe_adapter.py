"""Stripe Connect adapter - PaymentIntent and transfers."""

import logging
from typing import Any, Dict, List, Optional

import stripe

from config import settings
from db import get_order_with_items, get_partner_stripe_account

logger = logging.getLogger(__name__)


def _ensure_stripe_configured():
    if not settings.stripe_configured:
        raise ValueError("Stripe not configured (STRIPE_SECRET_KEY)")


async def create_payment_intent(
    order_id: str,
    amount_cents: int,
    currency: str = "usd",
) -> Dict[str, Any]:
    """
    Create Stripe PaymentIntent for order.
    For MVP: single PaymentIntent. Stripe Connect splits can be added via transfer_data later.
    Returns { client_secret, payment_intent_id }.
    """
    _ensure_stripe_configured()
    stripe.api_key = settings.stripe_secret_key

    # Build transfer_data for partner splits if partners have Stripe accounts
    order = await get_order_with_items(order_id)
    transfer_data = None
    if order and order.get("items"):
        # For each order item, get partner stripe_account_id and build application_fee_amount
        # Simplified: single payment, transfers handled in webhook
        pass

    pi = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        metadata={"order_id": order_id},
        automatic_payment_methods={"enabled": True},
    )
    return {
        "client_secret": pi.client_secret,
        "payment_intent_id": pi.id,
    }


async def create_sponsorship_payment_intent(
    product_id: str,
    partner_id: str,
    amount_cents: int,
    start_at: str,
    end_at: str,
    currency: str = "usd",
) -> Dict[str, Any]:
    """
    Create Stripe PaymentIntent for product sponsorship.
    Metadata includes type=sponsorship for webhook to create product_sponsorships row.
    Returns { client_secret, payment_intent_id }.
    """
    _ensure_stripe_configured()
    stripe.api_key = settings.stripe_secret_key

    pi = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        metadata={
            "type": "sponsorship",
            "product_id": product_id,
            "partner_id": partner_id,
            "start_at": start_at,
            "end_at": end_at,
            "amount_cents": str(amount_cents),
        },
        automatic_payment_methods={"enabled": True},
    )
    return {
        "client_secret": pi.client_secret,
        "payment_intent_id": pi.id,
    }


async def confirm_payment_intent(payment_intent_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve PaymentIntent (e.g. after confirmation)."""
    _ensure_stripe_configured()
    stripe.api_key = settings.stripe_secret_key
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError as e:
        logger.warning("Stripe retrieve failed: %s", e)
        return None
