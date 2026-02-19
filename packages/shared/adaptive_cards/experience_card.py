"""Experience bundle Adaptive Card - grouped by category (e.g. date night: flowers, dinner, transport).

Fulfillment requirements are derived dynamically from bundle categories:
- limo/transport/chauffeur: pickup_time, pickup_address
- flowers/delivery: delivery_address
- dinner/restaurant: delivery_address
"""

from typing import Any, Dict, List, Optional, Tuple

from .base import _filter_empty, container, create_card, strip_html, text_block

# Category keywords -> fulfillment fields. Used to derive required fields per bundle.
CATEGORY_FULFILLMENT_MAP: Dict[str, Tuple[str, ...]] = {
    "limo": ("pickup_time", "pickup_address"),
    "transport": ("pickup_time", "pickup_address"),
    "chauffeur": ("pickup_time", "pickup_address"),
    "ride": ("pickup_time", "pickup_address"),
    "flowers": ("delivery_address",),
    "flower": ("delivery_address",),
    "dinner": ("delivery_address",),
    "restaurant": ("delivery_address",),
    "chocolates": ("delivery_address",),
    "chocolate": ("delivery_address",),
    "delivery": ("delivery_address",),
    "gifts": ("delivery_address",),
    "gift": ("delivery_address",),
}

# Default when no category matches (full experience)
DEFAULT_FULFILLMENT_FIELDS = ("pickup_time", "pickup_address", "delivery_address")


def derive_fulfillment_fields(categories: List[str]) -> Tuple[str, ...]:
    """Derive required fulfillment fields from bundle categories. Returns sorted unique tuple."""
    if not categories:
        return DEFAULT_FULFILLMENT_FIELDS
    seen: set = set()
    for cat in categories:
        c = (cat or "").strip().lower()
        if not c:
            continue
        for key, fields in CATEGORY_FULFILLMENT_MAP.items():
            if key in c or c in key:
                seen.update(fields)
                break
    if not seen:
        return DEFAULT_FULFILLMENT_FIELDS
    # Preserve canonical order
    order = ("pickup_time", "pickup_address", "delivery_address")
    return tuple(f for f in order if f in seen)


def generate_experience_card(
    experience_name: str,
    categories: List[Dict[str, Any]],
    suggested_bundle_product_ids: Optional[List[str]] = None,
    suggested_bundle_options: Optional[List[Dict[str, Any]]] = None,
    fulfillment_hints: Optional[Dict[str, str]] = None,
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

    hints = fulfillment_hints or {}

    def _build_action_data(
        product_ids: List[str],
        option_label: str,
        opt_categories: List[str],
    ) -> Dict[str, Any]:
        fields = derive_fulfillment_fields(opt_categories)
        data: Dict[str, Any] = {
            "action": "add_bundle_bulk",
            "product_ids": product_ids,
            "option_label": option_label,
            "requires_fulfillment": bool(fields),
            "fulfillment_fields": list(fields),
        }
        for f in fields:
            if hints.get(f):
                data[f] = hints[f]
        return data

    if suggested_bundle_options:
        for opt in suggested_bundle_options:
            label = opt.get("label", "Option")
            product_ids = opt.get("product_ids") or []
            product_names = opt.get("product_names") or []
            total_price = opt.get("total_price")
            desc = opt.get("description", "")
            currency = opt.get("currency", "USD")
            opt_cats = [str(c) for c in (opt.get("categories") or []) if c]
            # Fancy description + product list (no individual prices) + bundle price only
            items = [text_block(f"**{label}**", size="Medium", weight="Bolder")]
            if desc:
                items.append(text_block(desc, size="Small"))
            if product_names:
                items.append(text_block("Includes: " + ", ".join(product_names), size="Small", is_subtle=True))
            if total_price is not None:
                items.append(text_block(f"{currency} {float(total_price):.2f} total", size="Medium", weight="Bolder"))
            action_data = _build_action_data(product_ids, label, opt_cats)
            items.append({
                "type": "ActionSet",
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": f"Add {label}",
                        "data": action_data,
                    },
                ],
            })
            body.append({
                "type": "Container",
                "items": items,
                "style": "emphasis",
            })
    elif suggested_bundle_product_ids:
        # Curated bundle: derive fields from top-level categories
        cat_queries = [str(c.get("query", "")) for c in categories if isinstance(c, dict) and c.get("query")]
        action_data = _build_action_data(suggested_bundle_product_ids, "", cat_queries)
        body.append({
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Add curated bundle",
                    "data": action_data,
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
