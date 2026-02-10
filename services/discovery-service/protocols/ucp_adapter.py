"""Google Universal Commerce Protocol (UCP) product feed parser."""

from typing import Any, Dict, List, Optional, Union


def parse_ucp_feed(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Parse Google UCP product feed format into unified product records.

    UCP is designed for AI agent product discovery (Google Search AI Mode, Gemini).
    Structure may vary; we support common product feed patterns.

    Returns list of dicts with: id, name, description, price, currency, image_url, etc.
    """
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "products" in data:
            items = data["products"]
        elif "items" in data:
            items = data["items"]
        elif "itemListElement" in data:
            items = data["itemListElement"]
        elif "offers" in data:
            items = data["offers"]
        else:
            items = [data]
    else:
        return []

    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        p = _parse_ucp_item(item)
        if p:
            result.append(p)
    return result


def _parse_ucp_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert single UCP item to unified product."""
    # UCP schema.org style: @type Product, name, description, offers
    item_id = item.get("itemId") or item.get("id") or item.get("identifier") or item.get("sku")
    name = item.get("name") or item.get("title") or ""
    description = item.get("description") or ""
    if not item_id and not name:
        return None

    # Offers: { price, priceCurrency }
    offers = item.get("offers") or item.get("offer")
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = float(offers.get("price", 0)) if offers else 0.0
    currency = offers.get("priceCurrency", "USD") if offers else "USD"

    # Image
    image_url = item.get("image") or item.get("image_url")
    if isinstance(image_url, list):
        image_url = image_url[0] if image_url else None

    return {
        "id": item_id,
        "name": name,
        "description": description,
        "price": price,
        "currency": currency,
        "url": item.get("url") or item.get("productUrl"),
        "image_url": image_url,
        "availability": item.get("availability", "in_stock"),
        "brand": item.get("brand", {}).get("name", "") if isinstance(item.get("brand"), dict) else item.get("brand", ""),
        "capabilities": item.get("capabilities", []),
        "metadata": {"source": "ucp"},
    }
