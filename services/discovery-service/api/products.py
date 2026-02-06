"""Product discovery API - Chat-First with JSON-LD and Adaptive Cards."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query, Request

from db import search_products, get_product_by_id, add_product_to_bundle, get_bundle_by_id
from packages.shared.adaptive_cards import generate_product_card, generate_bundle_card
from packages.shared.adaptive_cards.base import create_card, text_block

router = APIRouter(prefix="/api/v1", tags=["Discover"])


class AddToBundleBody(BaseModel):
    """Request body for adding a product to a bundle."""

    product_id: str
    user_id: Optional[str] = None
    bundle_id: Optional[str] = None


@router.get("/discover")
async def discover_products(
    request: Request,
    intent: str = Query(..., description="Search query (e.g. 'flowers', 'chocolates')"),
    location: Optional[str] = Query(None, description="Optional location filter"),
    partner_id: Optional[str] = Query(None, description="Filter by partner"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Discover products by intent/query.
    Chat-First: Returns JSON-LD and Adaptive Card for AI agents.
    """
    products = await search_products(query=intent, limit=limit, partner_id=partner_id)

    # Build JSON-LD ItemList (schema.org)
    item_list_elements = []
    for p in products:
        item_list_elements.append(
            {
                "@type": "Product",
                "name": p.get("name", ""),
                "description": p.get("description", ""),
                "offers": {
                    "@type": "Offer",
                    "price": float(p.get("price", 0)),
                    "priceCurrency": p.get("currency", "USD"),
                },
                "capabilities": p.get("capabilities", []),
                "identifier": str(p.get("id", "")),
            }
        )

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    return {
        "data": {
            "products": products,
            "count": len(products),
        },
        "machine_readable": {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "numberOfItems": len(products),
            "itemListElement": item_list_elements,
        },
        "adaptive_card": generate_product_card(products),
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }


@router.get("/products/{product_id}")
async def get_product(
    request: Request,
    product_id: str,
):
    """Get product by ID. For View Details action."""
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return {
        "data": product,
        "machine_readable": {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product.get("name"),
            "description": product.get("description"),
            "offers": {
                "@type": "Offer",
                "price": float(product.get("price", 0)),
                "priceCurrency": product.get("currency", "USD"),
            },
            "identifier": str(product.get("id")),
        },
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }


@router.get("/bundles/{bundle_id}")
async def get_bundle(request: Request, bundle_id: str):
    """Get bundle by ID with items. For View Bundle action."""
    bundle = await get_bundle_by_id(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    items = bundle.get("items", [])
    item_list = [
        {
            "@type": "Product",
            "name": item.get("name"),
            "offers": {"@type": "Offer", "price": item.get("price"), "priceCurrency": item.get("currency", "USD")},
        }
        for item in items
    ]
    return {
        "data": bundle,
        "machine_readable": {
            "@context": "https://schema.org",
            "@type": "Order",
            "orderNumber": str(bundle.get("id")),
            "name": bundle.get("name"),
            "totalPrice": float(bundle.get("total_price", 0)),
            "priceCurrency": bundle.get("currency", "USD"),
            "orderItemCount": len(items),
            "orderedItem": item_list,
        },
        "adaptive_card": generate_bundle_card(bundle),
        "summary": f"Bundle: {bundle.get('name', 'Your Bundle')} — {len(items)} item(s), {bundle.get('currency', 'USD')} {float(bundle.get('total_price', 0)):.2f}",
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }


@router.post("/bundle/add")
async def add_to_bundle(request: Request, body: AddToBundleBody):
    """Add product to bundle. For Add to Bundle action."""
    result = await add_product_to_bundle(
        product_id=body.product_id,
        user_id=body.user_id,
        bundle_id=body.bundle_id,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to add to bundle (product not found or error)")
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    summary = f"Added {result.get('product_added', 'product')} to bundle. Total: {result.get('currency', 'USD')} {float(result.get('total_price', 0)):.2f}"
    bundle_id = result.get("bundle_id")
    adaptive_card = create_card(
        body=[text_block(summary)],
        actions=[
            {"type": "Action.Submit", "title": "View Bundle", "data": {"action": "view_bundle", "bundle_id": str(bundle_id)}},
        ],
    ) if bundle_id else None
    return {
        "data": result,
        "summary": summary,
        "adaptive_card": adaptive_card,
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }
