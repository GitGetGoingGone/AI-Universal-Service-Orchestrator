"""Checkout Adaptive Card - order summary with instant checkout button."""

from typing import Any, Dict, List, Optional

from .base import create_card, fact_set, text_block


def generate_checkout_card(
    order: Dict[str, Any],
    *,
    line_items: Optional[List[Dict[str, Any]]] = None,
    show_instant_checkout: bool = True,
) -> Dict[str, Any]:
    """
    Generate Adaptive Card for order summary with instant checkout.
    Supports ChatGPT Instant Checkout for one-click purchases.
    """
    body = [
        text_block("Order Summary", size="Large", weight="Bolder"),
    ]

    # Line items
    items = line_items or order.get("line_items", [])
    for item in items:
        name = item.get("name", "Item")
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        currency = item.get("currency", "USD")
        subtotal = float(price) * int(qty)
        body.append(
            {
                "type": "Container",
                "items": [
                    text_block(f"{name} × {qty}", weight="Bolder"),
                    text_block(f"{currency} {subtotal:.2f}", size="Small"),
                ],
            }
        )

    # Totals
    facts = []
    if order.get("subtotal") is not None:
        currency = order.get("currency", "USD")
        facts.append({"title": "Subtotal", "value": f"{currency} {float(order['subtotal']):.2f}"})
    if order.get("tax"):
        currency = order.get("currency", "USD")
        facts.append({"title": "Tax", "value": f"{currency} {float(order['tax']):.2f}"})
    if order.get("shipping"):
        currency = order.get("currency", "USD")
        facts.append({"title": "Shipping", "value": f"{currency} {float(order['shipping']):.2f}"})
    if order.get("total") is not None:
        currency = order.get("currency", "USD")
        facts.append({"title": "Total", "value": f"{currency} {float(order['total']):.2f}"})
    if facts:
        body.append(fact_set(facts))

    # Delivery/notes
    if order.get("delivery_address"):
        body.append(text_block(f"Deliver to: {order['delivery_address']}", size="Small", is_subtle=True))
    if order.get("notes"):
        body.append(text_block(f"Note: {order['notes']}", size="Small", is_subtle=True))

    actions = []
    if show_instant_checkout:
        actions = [
            {"type": "Action.Submit", "title": "Complete Checkout", "data": {"action": "complete_checkout", "order_id": str(order.get("id", ""))}},
            {"type": "Action.Submit", "title": "Edit Order", "data": {"action": "edit_order"}},
        ]

    return create_card(body=body, actions=actions)
