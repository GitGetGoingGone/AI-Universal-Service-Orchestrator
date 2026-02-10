"""Schema.org JSON-LD for Product / ItemList."""

from typing import Any, Dict, List, Optional


def product_ld(
    product_id: str,
    name: str,
    description: Optional[str] = None,
    price: Optional[float] = None,
    currency: str = "USD",
    capabilities: Optional[List[str]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Single product as Schema.org Product."""
    out: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Product",
        "identifier": product_id,
        "name": name,
    }
    if description:
        out["description"] = description
    if price is not None:
        out["offers"] = {
            "@type": "Offer",
            "price": price,
            "priceCurrency": currency,
        }
    if capabilities:
        out["category"] = ", ".join(capabilities)
    out.update(kwargs)
    return out


def product_list_ld(
    products: List[Dict[str, Any]],
    count: Optional[int] = None,
) -> Dict[str, Any]:
    """ItemList of Product for discovery response."""
    items = []
    for p in products:
        items.append(
            product_ld(
                product_id=str(p.get("id", "")),
                name=p.get("name", "Unknown"),
                description=p.get("description"),
                price=float(p["price"]) if p.get("price") is not None else None,
                currency=p.get("currency", "USD"),
                capabilities=p.get("capabilities") if isinstance(p.get("capabilities"), list) else None,
            )
        )
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "numberOfItems": count if count is not None else len(items),
        "itemListElement": items,
    }
