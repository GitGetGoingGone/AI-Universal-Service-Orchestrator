"""
Public product shape for UCP and gateway-proxied responses.
Strip internal-only fields (experience_tags, partner_id, internal_notes) from all client-facing responses.
Use this allow-list in Discovery and Gateway when returning products to clients.
"""

from typing import Any, Dict, List

# Keys allowed in public product / UCP item responses. All other keys are stripped.
PUBLIC_PRODUCT_ALLOWED_KEYS = frozenset({
    "id",
    "name",
    "title",
    "description",
    "price",
    "currency",
    "image_url",
    "url",
    "brand",
    "capabilities",
    "metadata",
    "created_at",
    "sold_count",
})

# Explicitly strip these if present (internal-only)
STRIP_KEYS = frozenset({
    "experience_tags",
    "partner_id",
    "internal_notes",
})


def filter_product_for_public(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a shallow copy of product with only allowed keys.
    Strips experience_tags, partner_id, internal_notes and any key not in PUBLIC_PRODUCT_ALLOWED_KEYS.
    """
    if not product or not isinstance(product, dict):
        return {}
    return {
        k: v for k, v in product.items()
        if k in PUBLIC_PRODUCT_ALLOWED_KEYS and k not in STRIP_KEYS
    }


def filter_products_for_public(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply filter_product_for_public to each product in the list."""
    return [filter_product_for_public(p) for p in products]
