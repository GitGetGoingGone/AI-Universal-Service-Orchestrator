"""Experience bundle Adaptive Card - grouped by category (e.g. date night: flowers, dinner, transport)."""

from typing import Any, Dict, List, Optional

from .base import _filter_empty, container, create_card, strip_html, text_block


def generate_experience_card(
    experience_name: str,
    categories: List[Dict[str, Any]],
    suggested_bundle_product_ids: Optional[List[str]] = None,
    suggested_bundle_options: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate Adaptive Card for experience bundle.
    Header: experience_name. Sections per category with products.
    Same actions per product: Add to Bundle, View Details.
    When suggested_bundle_options (2-4 options): one "Add this bundle" per option.
    When suggested_bundle_product_ids (single): one "Add curated bundle" button.
    """
    title = (experience_name or "experience").replace("_", " ").title()
    body: List[Dict[str, Any]] = [
        text_block(f"Your {title} bundle", size="Large", weight="Bolder"),
    ]

    if suggested_bundle_options:
        for opt in suggested_bundle_options:
            label = opt.get("label", "Option")
            product_ids = opt.get("product_ids") or []
            total_price = opt.get("total_price")
            desc = opt.get("description", "")
            btn_title = f"Add {label}"
            if total_price is not None:
                btn_title = f"Add {label} (${float(total_price):.2f})"
            body.append({
                "type": "Container",
                "items": [
                    text_block(f"**{label}**" + (f" – {desc}" if desc else ""), size="Small"),
                    {
                        "type": "ActionSet",
                        "actions": [
                            {
                                "type": "Action.Submit",
                                "title": btn_title,
                                "data": {
                                    "action": "add_bundle_bulk",
                                    "product_ids": product_ids,
                                    "option_label": label,
                                },
                            },
                        ],
                    },
                ],
                "style": "emphasis",
            })
    elif suggested_bundle_product_ids:
        body.append({
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Add curated bundle",
                    "data": {
                        "action": "add_bundle_bulk",
                        "product_ids": suggested_bundle_product_ids,
                    },
                },
            ],
        })

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
