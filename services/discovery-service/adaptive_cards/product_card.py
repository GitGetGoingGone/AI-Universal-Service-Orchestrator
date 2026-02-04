"""Product Adaptive Card generator for Chat-First (Gemini, ChatGPT)."""

from typing import Any, Dict, List


def generate_product_card(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate Adaptive Card for product list.
    Supports Gemini Dynamic View and ChatGPT native rendering.
    """
    if not products:
        return {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "No products found.",
                    "wrap": True,
                }
            ],
        }

    body = [
        {
            "type": "TextBlock",
            "text": f"Found {len(products)} product(s)",
            "size": "Medium",
            "weight": "Bolder",
            "wrap": True,
        }
    ]

    for p in products:
        name = p.get("name", "Unknown")
        description = (p.get("description") or "")[:100]
        price = p.get("price", 0)
        currency = p.get("currency", "USD")
        capabilities = p.get("capabilities") or []
        caps_str = ", ".join(capabilities) if isinstance(capabilities, list) else str(capabilities)

        body.append(
            {
                "type": "Container",
                "style": "emphasis",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": name,
                        "weight": "Bolder",
                        "wrap": True,
                    },
                    {
                        "type": "TextBlock",
                        "text": f"{currency} {price:.2f}",
                        "size": "Small",
                        "wrap": True,
                    },
                    (
                        {
                            "type": "TextBlock",
                            "text": caps_str,
                            "size": "Small",
                            "isSubtle": True,
                            "wrap": True,
                        }
                        if caps_str
                        else {}
                    ),
                    (
                        {
                            "type": "TextBlock",
                            "text": description,
                            "size": "Small",
                            "wrap": True,
                        }
                        if description
                        else {}
                    ),
                ],
                "actions": [
                    {
                        "type": "Action.Submit",
                        "title": "Add to Bundle",
                        "data": {"action": "add_to_bundle", "product_id": str(p.get("id", ""))},
                    },
                    {
                        "type": "Action.Submit",
                        "title": "View Details",
                        "data": {"action": "view_details", "product_id": str(p.get("id", ""))},
                    },
                ],
            }
        )
        # Remove empty items
        body[-1]["items"] = [i for i in body[-1]["items"] if i]
        body[-1]["actions"] = [a for a in body[-1]["actions"] if a]

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": body,
    }
