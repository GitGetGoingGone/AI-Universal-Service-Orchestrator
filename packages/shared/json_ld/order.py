"""Schema.org JSON-LD for Order."""

from typing import Any, Dict, List, Optional


def order_ld(
    order_id: str,
    status: Optional[str] = None,
    order_date: Optional[str] = None,
    items: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Order as Schema.org Order."""
    out: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Order",
        "identifier": order_id,
    }
    if status:
        out["orderStatus"] = status
    if order_date:
        out["orderDate"] = order_date
    if items:
        out["orderItem"] = [
            {
                "@type": "OrderItem",
                "name": i.get("name", "Item"),
                "quantity": i.get("quantity", 1),
                "unitPrice": i.get("price"),
            }
            for i in items
        ]
    out.update(kwargs)
    return out
