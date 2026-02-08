"""Main autonomous recovery logic - handle partner rejection."""

import logging
from typing import Any, Dict, Optional

from clients import discover_products
from db import (
    get_negotiation,
    get_order,
    get_order_leg,
    cancel_order_leg,
    get_bundle_leg,
    add_product_to_bundle,
    add_order_item_and_leg,
    create_autonomous_recovery,
    create_escalation,
)

logger = logging.getLogger(__name__)


def _extract_search_query(original_request: Dict[str, Any]) -> str:
    """Extract search query from requested_change for Discovery."""
    req = original_request.get("requested_change", {}) or original_request
    if isinstance(req, dict):
        desc = req.get("description") or req.get("requested_item") or req.get("query")
        if desc:
            return str(desc)
    if isinstance(req, str):
        return req
    return "product"


async def handle_partner_rejection(
    negotiation_id: str,
    rejection_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Handle partner rejection: cancel leg, find alternative, update bundle/order.
    Returns result dict with success, narrative, adaptive_card for user notification.
    """
    negotiation = await get_negotiation(negotiation_id)
    if not negotiation:
        return {"success": False, "error": "Negotiation not found"}

    order_id = negotiation.get("order_id")
    order_leg_id = negotiation.get("order_leg_id")
    partner_id = negotiation.get("partner_id")
    original_request = negotiation.get("original_request") or {}

    order = await get_order(order_id)
    if not order:
        return {"success": False, "error": "Order not found"}

    order_leg = await get_order_leg(order_leg_id)
    if not order_leg:
        return {"success": False, "error": "Order leg not found"}

    bundle_leg_id = order_leg.get("bundle_leg_id")
    bundle_id = order.get("bundle_id")
    original_item = original_request.get("original_item", {})

    # 1. Cancel original order leg
    await cancel_order_leg(order_leg_id)

    # 2. Find alternative via Discovery
    search_query = _extract_search_query(original_request)
    alternatives = await discover_products(
        query=search_query,
        limit=5,
        exclude_partner_id=str(partner_id) if partner_id else None,
    )

    if not alternatives:
        # Escalate - no alternative found
        await create_escalation(negotiation_id, "no_alternative_found")
        await create_autonomous_recovery(
            order_id=order_id,
            original_leg_id=order_leg_id,
            change_request=original_request,
            partner_rejection=rejection_payload,
            recovery_action="escalated",
        )
        return {
            "success": False,
            "escalated": True,
            "narrative": f"No alternative found for '{search_query}'. Escalated for human review.",
            "adaptive_card": None,
        }

    # 3. Pick best alternative (first one, optionally rank by price later)
    alt = alternatives[0]
    alt_product_id = str(alt.get("id", ""))
    alt_partner_id = alt.get("partner_id")
    alt_name = alt.get("name", "Alternative")
    alt_price = float(alt.get("price", 0))

    # 4. Add to bundle and order
    new_leg = await add_product_to_bundle(
        bundle_id=bundle_id,
        product_id=alt_product_id,
        partner_id=alt_partner_id,
        price=alt_price,
    )
    if not new_leg:
        await create_escalation(negotiation_id, "bundle_update_failed")
        return {"success": False, "error": "Failed to update bundle"}

    await add_order_item_and_leg(
        order_id=order_id,
        product_id=alt_product_id,
        partner_id=alt_partner_id,
        item_name=alt_name,
        unit_price=alt_price,
        bundle_leg_id=str(new_leg["id"]),
    )

    # 5. Create recovery record
    await create_autonomous_recovery(
        order_id=order_id,
        original_leg_id=order_leg_id,
        change_request=original_request,
        partner_rejection=rejection_payload,
        recovery_action="found_alternative",
        alternative_item_id=alt_product_id,
        alternative_vendor_id=str(alt_partner_id) if alt_partner_id else None,
        timeline_changed=False,
        delay_minutes=None,
    )

    original_name = original_item.get("name", "original item")
    narrative = f"I've found '{alt_name}' from a different vendor to replace '{original_name}'. Your order has been updated."
    return {
        "success": True,
        "narrative": narrative,
        "original_item": original_item,
        "new_item": {"id": alt_product_id, "name": alt_name, "price": alt_price, "partner_id": alt_partner_id},
        "adaptive_card": {
            "type": "AdaptiveCard",
            "body": [
                {"type": "TextBlock", "text": narrative, "wrap": True},
                {"type": "TextBlock", "text": f"New item: {alt_name} - ${alt_price:.2f}", "wrap": True},
            ],
        },
    }
