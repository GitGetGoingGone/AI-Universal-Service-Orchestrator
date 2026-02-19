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
            product_names = opt.get("product_names") or []
            total_price = opt.get("total_price")
            desc = opt.get("description", "")
            currency = opt.get("currency", "USD")
            # Fancy description + product list (no individual prices) + bundle price only
            items = [text_block(f"**{label}**", size="Medium", weight="Bolder")]
            if desc:
                items.append(text_block(desc, size="Small"))
            if product_names:
                items.append(text_block("Includes: " + ", ".join(product_names), size="Small", is_subtle=True))
            if total_price is not None:
                items.append(text_block(f"{currency} {float(total_price):.2f} total", size="Medium", weight="Bolder"))
            items.append({
                "type": "ActionSet",
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": f"Add {label}",
                        "data": {
                            "action": "add_bundle_bulk",
                            "product_ids": product_ids,
                            "option_label": label,
                        },
                    },
                ],
            })
            body.append({
                "type": "Container",
                "items": items,
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

    # When we have bundle options, skip category sections (products already listed in each option; no individual prices)
    if suggested_bundle_options:
        return create_card(body=body)

    for cat in categories:
        query = cat.get("query", "products")
        products = cat.get("products") or []
        section_title = query.replace("_", " ").title() if isinstance(query, str) else "Products"
        body.append(text_block(section_title, size="Medium", weight="Bolder"))

        if not products:
            # Truncate long category names (e.g. from bad intent derivation)
            qstr = str(query) if isinstance(query, str) else "products"
            display_query = (qstr[:40] + "…") if len(qstr) > 40 else qstr
            body.append(text_block(f"No {display_query} found.", size="Small", is_subtle=True))
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
