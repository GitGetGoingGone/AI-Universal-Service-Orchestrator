"""Bundle Adaptive Card - composition with timeline."""

from typing import Any, Dict, List, Optional

from .base import create_card, fact_set, text_block


def generate_bundle_card(
    bundle: Dict[str, Any],
    *,
    items: Optional[List[Dict[str, Any]]] = None,
    timeline: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate Adaptive Card for bundle composition with optional timeline.
    """
    body = [
        text_block(bundle.get("name", "Your Bundle"), size="Large", weight="Bolder"),
        text_block(bundle.get("description", ""), size="Small", is_subtle=True) if bundle.get("description") else None,
    ]
    body = [b for b in body if b]

    # Bundle summary facts
    facts = []
    if bundle.get("total_price") is not None:
        currency = bundle.get("currency", "USD")
        facts.append({"title": "Total", "value": f"{currency} {float(bundle['total_price']):.2f}"})
    if bundle.get("item_count"):
        facts.append({"title": "Items", "value": str(bundle["item_count"])})
    if bundle.get("estimated_delivery"):
        facts.append({"title": "Est. Delivery", "value": str(bundle["estimated_delivery"])})
    if facts:
        body.append(fact_set(facts))

    # Items in bundle
    bundle_items = items or bundle.get("items", [])
    if bundle_items:
        body.append(text_block("Items in bundle", size="Medium", weight="Bolder"))
        for item in bundle_items:
            name = item.get("name", "Unknown")
            price = item.get("price", 0)
            currency = item.get("currency", "USD")
            body.append(
                {
                    "type": "Container",
                    "style": "emphasis",
                    "items": [
                        text_block(name, weight="Bolder"),
                        text_block(f"{currency} {price:.2f}", size="Small"),
                    ],
                    "actions": [
                        {"type": "Action.Submit", "title": "Remove", "data": {"action": "remove_from_bundle", "item_id": str(item.get("id", ""))}},
                    ],
                }
            )

    # Timeline (multi-leg journey)
    timeline_data = timeline or bundle.get("timeline", [])
    if timeline_data:
        body.append(text_block("Timeline", size="Medium", weight="Bolder"))
        for leg in timeline_data:
            leg_name = leg.get("name", "Leg")
            eta = leg.get("eta") or leg.get("deadline", "—")
            body.append(
                {
                    "type": "Container",
                    "items": [
                        text_block(f"• {leg_name}", weight="Bolder"),
                        text_block(f"ETA: {eta}", size="Small", is_subtle=True),
                    ],
                }
            )

    actions = [
        {"type": "Action.Submit", "title": "Proceed to Checkout", "data": {"action": "checkout", "bundle_id": str(bundle.get("id", ""))}},
        {"type": "Action.Submit", "title": "Add More", "data": {"action": "add_more"}},
    ]

    return create_card(body=body, actions=actions)
