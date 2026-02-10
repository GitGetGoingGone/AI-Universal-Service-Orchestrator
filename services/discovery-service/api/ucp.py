"""UCP (Google Universal Commerce Protocol) catalog API for Gemini discovery."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from db import search_products, get_partner_by_id
from protocols.ucp_compliance import _normalize_for_ucp

router = APIRouter(prefix="/api/v1/ucp", tags=["UCP"])


def _product_to_ucp_item(product: Dict[str, Any], partner: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Map internal product to UCP Item: id, title, price (integer cents), optional image_url, seller_name."""
    p = _normalize_for_ucp(product)
    price = p.get("price")
    if price is None:
        price_cents = 0
    elif isinstance(price, (int, float)):
        # Assume major units (e.g. 19.99); convert to cents
        currency = product.get("currency", "USD")
        if currency and currency.upper() != "USD":
            price_cents = int(round(float(price) * 100))
        else:
            price_cents = int(round(float(price) * 100))
    else:
        price_cents = 0
    item: Dict[str, Any] = {
        "id": str(product.get("id", "")),
        "title": p.get("title") or p.get("name") or "",
        "price": price_cents,
    }
    if p.get("image_url"):
        item["image_url"] = p["image_url"]
    if partner:
        seller_name = partner.get("seller_name") or partner.get("business_name")
        if seller_name:
            item["seller_name"] = seller_name
    return item


@router.get("/items")
async def ucp_items(
    q: str = Query("", description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    partner_id: Optional[str] = Query(None, description="Filter by partner"),
):
    """
    UCP catalog: search/browse products as UCP Item shape (id, title, price in cents, image_url).
    Used by Gemini/Google when they discover us via /.well-known/ucp.
    """
    products = await search_products(query=q or "", limit=limit, partner_id=partner_id)
    partner_ids = list({str(p["partner_id"]) for p in products if p.get("partner_id")})
    partners_map: Dict[str, Dict[str, Any]] = {}
    for pid in partner_ids:
        partner = await get_partner_by_id(pid)
        if partner:
            partners_map[pid] = partner
    items: List[Dict[str, Any]] = []
    for p in products:
        pid = str(p.get("partner_id", "")) if p.get("partner_id") else ""
        partner = partners_map.get(pid) if pid else None
        items.append(_product_to_ucp_item(p, partner))
    return {"items": items}
