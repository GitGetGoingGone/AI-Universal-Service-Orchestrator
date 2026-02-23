"""UCP (Google Universal Commerce Protocol) catalog API for Gemini discovery."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from db import get_partner_by_id
from packages.shared.discovery import derive_search_query, is_browse_query
from packages.shared.ucp_public_product import filter_product_for_public
from protocols.ucp_compliance import _normalize_for_ucp
from scout_engine import search as scout_search

router = APIRouter(prefix="/api/v1/ucp", tags=["UCP"])

# Path to OpenAPI schema (sibling to api/)
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "rest.openapi.json"


@router.get("/rest.openapi.json")
async def ucp_rest_openapi():
    """
    Serve the UCP REST OpenAPI schema. Referenced by /.well-known/ucp under rest.schema.
    AI agents use this to discover searchGifts and checkout operations.
    """
    if not _SCHEMA_PATH.exists():
        return JSONResponse(status_code=404, content={"error": "Schema not found"})
    data = json.loads(_SCHEMA_PATH.read_text())
    return JSONResponse(
        content=data,
        headers={
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=3600",
        },
    )


def _product_to_ucp_item(product: Dict[str, Any], partner: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Map internal product to UCP Item: id, title, price (integer cents), optional image_url, seller_name. Uses public allow-list to strip internal fields."""
    p = _normalize_for_ucp(filter_product_for_public(product))
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


# Occasion/recipient keywords for query augmentation (beads/bridge logic)
_OCCASION_KEYWORDS = {
    "birthday": "birthday gift",
    "anniversary": "anniversary gift",
    "baby_shower": "baby shower gift",
    "wedding": "wedding gift",
    "holiday": "holiday gift",
    "thank_you": "thank you gift",
    "get_well": "get well gift",
    "graduation": "graduation gift",
    "general": "gift",
}
_RECIPIENT_KEYWORDS = {
    "her": "for her",
    "him": "for him",
    "them": "gift",
    "baby": "baby",
    "couple": "for couple",
    "family": "for family",
    "any": "",
}


@router.get("/items")
async def ucp_items(
    q: str = Query("", description="Natural language search query"),
    limit: int = Query(20, ge=1, le=100),
    partner_id: Optional[str] = Query(None, description="Filter by partner"),
    occasion: Optional[str] = Query(None, description="Gift occasion for relevance"),
    budget_max: Optional[int] = Query(None, ge=0, description="Max budget in cents"),
    recipient_type: Optional[str] = Query(None, description="Recipient type for relevance"),
):
    """
    UCP catalog: search/browse products as UCP Item shape (id, title, price in cents, image_url).
    operationId: searchGifts. Pass natural language to q; optional occasion, budget_max, recipient_type.
    """
    # Browse terms (products, items, what, etc.) → return catalog without filter
    raw_query = (q or "").strip().lower()
    if is_browse_query(raw_query) or raw_query in ("products", "items", "browse", "what"):
        search_query = ""
    else:
        # Action-word stripping: "wanna book limo service" -> "limo"
        base_query = derive_search_query(q) if " " in (q or "").strip() else (q or "").strip()
        search_parts = [base_query] if base_query else [q.strip()]
        if occasion and occasion in _OCCASION_KEYWORDS:
            search_parts.append(_OCCASION_KEYWORDS[occasion])
        if recipient_type and recipient_type in _RECIPIENT_KEYWORDS and _RECIPIENT_KEYWORDS[recipient_type]:
            search_parts.append(_RECIPIENT_KEYWORDS[recipient_type])
        search_query = " ".join(search_parts)

    # Empty query = browse (scout returns all products); otherwise use search
    products = await scout_search(
        query=search_query if search_query else "",  # "" triggers browse in scout
        limit=limit * 2 if budget_max else limit,
        partner_id=partner_id,
    )

    # Filter by budget_max (price in cents) if provided
    if budget_max is not None:
        filtered = []
        for p in products:
            price = p.get("price")
            if price is not None:
                price_cents = int(round(float(price) * 100))
                if price_cents <= budget_max:
                    filtered.append(p)
            else:
                filtered.append(p)
        products = filtered[:limit]
    else:
        products = products[:limit]

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
