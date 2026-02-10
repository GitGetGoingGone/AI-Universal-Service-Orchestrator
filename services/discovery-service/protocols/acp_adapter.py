"""OpenAI Agentic Commerce Protocol (ACP) product feed parser."""

from typing import Any, Dict, List, Optional, Union


def parse_acp_feed(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Parse ACP Product Feed format into unified product records.

    ACP supports: JSONL (array of objects), CSV, TSV.
    Required fields: item_id, title, description, url, price, image_url, availability, brand,
                    is_eligible_search, is_eligible_checkout

    Returns list of dicts with: id, name, description, price, currency, image_url, availability, etc.
    """
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "products" in data:
            items = data["products"]
        elif "items" in data:
            items = data["items"]
        else:
            items = [data]
    else:
        return []

    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        p = _parse_acp_item(item)
        if p:
            result.append(p)
    return result


def _parse_acp_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert single ACP item to unified product."""
    item_id = item.get("item_id") or item.get("id") or item.get("offer_id")
    title = item.get("title") or item.get("name") or ""
    description = item.get("description") or ""
    if not item_id and not title:
        return None

    # Price: "79.99 USD" format
    price_str = item.get("price") or "0"
    price = 0.0
    currency = "USD"
    if isinstance(price_str, (int, float)):
        price = float(price_str)
    else:
        parts = str(price_str).strip().split()
        if len(parts) >= 1:
            try:
                price = float(parts[0])
            except ValueError:
                pass
        if len(parts) >= 2:
            currency = parts[1]

    # Only include if eligible for search
    eligible = item.get("is_eligible_search", True)
    if isinstance(eligible, str):
        eligible = eligible.lower() in ("true", "1", "yes")
    if not eligible:
        return None

    return {
        "id": item_id,
        "name": title,
        "description": description,
        "price": price,
        "currency": currency,
        "url": item.get("url"),
        "image_url": item.get("image_url") or item.get("image"),
        "availability": item.get("availability", "in_stock"),
        "brand": item.get("brand", ""),
        "capabilities": [],
        "metadata": {"source": "acp", "brand": item.get("brand")},
    }
