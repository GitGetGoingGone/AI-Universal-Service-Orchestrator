"""Experience bundle Adaptive Card - grouped by category (e.g. date night: flowers, dinner, transport)."""

from typing import Any, Dict, List

from .base import _filter_empty, container, create_card, strip_html, text_block


def generate_experience_card(
    experience_name: str,
    categories: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate Adaptive Card for experience bundle.
    Header: experience_name. Sections per category with products.
    Same actions per product: Add to Bundle, View Details.
    """
    title = (experience_name or "experience").replace("_", " ").title()
    body: List[Dict[str, Any]] = [
        text_block(f"Your {title} bundle", size="Large", weight="Bolder"),
    ]

    for cat in categories:
        query = cat.get("query", "products")
        products = cat.get("products") or []
        section_title = query.replace("_", " ").title() if isinstance(query, str) else "Products"
        body.append(text_block(section_title, size="Medium", weight="Bolder"))

        if not products:
            body.append(text_block(f"No {section_title.lower()} found.", size="Small", is_subtle=True))
            continue

        for p in products:
            name = p.get("name", "Unknown")
            price = p.get("price", 0)
            currency = p.get("currency", "USD")
            description = strip_html(p.get("description") or "")[:80]
            image_url = p.get("image_url") or p.get("image")
            capabilities = p.get("capabilities") or []
            caps_str = ", ".join(capabilities) if isinstance(capabilities, list) else ""

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
                {"type": "Action.Submit", "title": "Add to Bundle", "data": {"action": "add_to_bundle", "product_id": str(p.get("id", ""))}},
                {"type": "Action.Submit", "title": "Favorite", "data": {"action": "add_to_favorites", "product_id": str(p.get("id", "")), "product_name": name}},
                {"type": "Action.Submit", "title": "Details", "data": {"action": "view_details", "product_id": str(p.get("id", ""))}},
            ]
            product_container = container(_filter_empty(items), style="emphasis", actions=actions)
            product_container["minHeight"] = "140px"
            body.append(product_container)

    return create_card(body=body)
