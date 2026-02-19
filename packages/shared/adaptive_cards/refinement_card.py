"""Adaptive Card for category refinement - 'Replace with this' alternatives."""

from typing import Any, Dict, List

from .base import _filter_empty, container, create_card, strip_html, text_block


def generate_refinement_card(
    products: List[Dict[str, Any]],
    bundle_id: str,
    leg_id: str,
    category: str,
) -> Dict[str, Any]:
    """
    Generate card for category refinement. Each product has "Replace with this" action.
    """
    if not products:
        return create_card(
            body=[text_block(f"No alternatives found for {category}.")],
        )

    title = (category or "category").replace("_", " ").title()
    body: List[Dict[str, Any]] = [
        text_block(f"Choose a replacement for {title}", size="Medium", weight="Bolder"),
    ]

    for p in products:
        name = p.get("name", "Unknown")
        description = strip_html(p.get("description") or "")[:80]
        price = p.get("price", 0)
        currency = p.get("currency", "USD")
        capabilities = p.get("capabilities") or []
        caps_str = ", ".join(capabilities) if isinstance(capabilities, list) else str(capabilities)
        image_url = p.get("image_url") or p.get("image")

        items = [
            text_block(name, weight="Bolder"),
            text_block(f"{currency} {price:.2f}", size="Small"),
        ]
        if caps_str:
            items.append(text_block(caps_str, size="Small", is_subtle=True))
        if description:
            items.append(text_block(description, size="Small"))
        if image_url:
            items.insert(1, {"type": "Image", "url": image_url, "size": "Medium"})

        actions = [
            {
                "type": "Action.Submit",
                "title": "Replace with this",
                "data": {
                    "action": "replace_in_bundle",
                    "bundle_id": bundle_id,
                    "leg_id": leg_id,
                    "product_id": str(p.get("id", "")),
                },
            },
            {"type": "Action.Submit", "title": "Details", "data": {"action": "view_details", "product_id": str(p.get("id", ""))}},
        ]

        product_container = container(_filter_empty(items), style="emphasis", actions=actions)
        product_container["minHeight"] = "140px"
        body.append(product_container)

    return create_card(body=body)
