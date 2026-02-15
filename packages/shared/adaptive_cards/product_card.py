"""Product Adaptive Card generator for Chat-First (Gemini, ChatGPT)."""

from typing import Any, Dict, List

from .base import _filter_empty, container, create_card, strip_html, text_block


def generate_product_card(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate Adaptive Card for product list.
    Supports Gemini Dynamic View and ChatGPT native rendering.
    """
    if not products:
        return create_card(
            body=[text_block("No products found.")],
        )

    body = [
        text_block(f"Found {len(products)} product(s)", size="Medium", weight="Bolder"),
    ]

    for p in products:
        name = p.get("name", "Unknown")
        description = strip_html(p.get("description") or "")[:100]
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
            {"type": "Action.Submit", "title": "Add to Cart", "data": {"action": "add_to_bundle", "product_id": str(p.get("id", ""))}},
            {"type": "Action.Submit", "title": "View Details", "data": {"action": "view_details", "product_id": str(p.get("id", ""))}},
        ]

        body.append(
            container(
                _filter_empty(items),
                style="emphasis",
                actions=actions,
            )
        )

    return create_card(body=body)
