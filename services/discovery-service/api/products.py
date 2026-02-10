"""Product discovery API - Chat-First with JSON-LD and Adaptive Cards."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query, Request

from db import get_product_by_id, get_products_for_acp_export, add_product_to_bundle, get_bundle_by_id, remove_from_bundle, create_order_from_bundle
from scout_engine import search
from protocols.acp_compliance import validate_product_acp
from protocols.ucp_compliance import validate_product_ucp
from packages.shared.adaptive_cards import generate_product_card, generate_bundle_card, generate_checkout_card
from packages.shared.adaptive_cards.base import create_card, text_block

router = APIRouter(prefix="/api/v1", tags=["Discover"])


class AddToBundleBody(BaseModel):
    """Request body for adding a product to a bundle."""

    product_id: str
    user_id: Optional[str] = None
    bundle_id: Optional[str] = None


class RemoveFromBundleBody(BaseModel):
    """Request body for removing an item from a bundle."""

    item_id: str  # bundle_leg id from bundle card


class CheckoutBody(BaseModel):
    """Request body for proceeding to checkout."""

    bundle_id: str


@router.get("/discover")
async def discover_products(
    request: Request,
    intent: str = Query(..., description="Search query (e.g. 'flowers', 'chocolates')"),
    location: Optional[str] = Query(None, description="Optional location filter"),
    partner_id: Optional[str] = Query(None, description="Filter by partner"),
    exclude_partner_id: Optional[str] = Query(None, description="Exclude partner (for re-sourcing)"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Discover products by intent/query.
    Chat-First: Returns JSON-LD and Adaptive Card for AI agents.
    """
    products = await search(
        query=intent, limit=limit, partner_id=partner_id, exclude_partner_id=exclude_partner_id
    )

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


def _product_to_acp_row_for_validation(product: dict) -> dict:
    """Build one ACP row from product (with partner seller fields) for validation."""
    price = float(product.get("price", 0))
    currency = product.get("currency", "USD") or "USD"
    availability = product.get("availability")
    if availability is None or availability == "":
        is_avail = product.get("is_available", True)
        availability = "in_stock" if is_avail else "out_of_stock"
    target_countries = product.get("target_countries")
    if target_countries is None:
        target_countries = []
    if isinstance(target_countries, str):
        target_countries = [target_countries] if target_countries else []
    row = {
        "item_id": str(product.get("id", "")),
        "title": (product.get("name") or "")[:150],
        "description": (product.get("description") or "")[:5000],
        "url": product.get("url") or "",
        "image_url": product.get("image_url") or "",
        "price": f"{price:.2f} {currency}",
        "availability": availability,
        "brand": (product.get("brand") or "")[:70],
        "is_eligible_search": bool(product.get("is_eligible_search", True)),
        "is_eligible_checkout": bool(product.get("is_eligible_checkout", False)),
        "seller_name": (product.get("seller_name") or "")[:70],
        "seller_url": product.get("seller_url") or "",
        "return_policy": product.get("return_policy") or "",
        "target_countries": target_countries,
        "store_country": product.get("store_country") or "",
    }
    if row.get("is_eligible_checkout"):
        row["seller_privacy_policy"] = product.get("seller_privacy_policy") or ""
        row["seller_tos"] = product.get("seller_tos") or ""
    return row


@router.get("/products/{product_id}/validate-discovery")
async def validate_product_discovery(product_id: str):
    """
    Validate product for ACP (ChatGPT) and UCP (Gemini) discovery.
    Loads product and partner from DB, builds combined record, runs validation.
    Returns { acp: { valid, errors, warnings }, ucp: { valid, errors } }.
    """
    products = await get_products_for_acp_export(product_id=product_id)
    if not products:
        raise HTTPException(status_code=404, detail="Product not found")
    combined = products[0]
    acp_row = _product_to_acp_row_for_validation(combined)
    require_checkout = bool(combined.get("is_eligible_checkout"))
    acp_valid, acp_missing, acp_violations = validate_product_acp(
        acp_row, require_checkout_fields=require_checkout
    )
    ucp_valid, ucp_missing, ucp_violations = validate_product_ucp(combined)
    return {
        "acp": {
            "valid": acp_valid,
            "errors": acp_missing + acp_violations,
            "warnings": [],
        },
        "ucp": {
            "valid": ucp_valid,
            "errors": ucp_missing + ucp_violations,
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


@router.post("/checkout")
async def proceed_to_checkout(request: Request, body: CheckoutBody):
    """Proceed to checkout with bundle. Creates order and returns order_id for payment."""
    bundle = await get_bundle_by_id(body.bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    items = bundle.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="Bundle is empty; add items before checkout")

    order = await create_order_from_bundle(body.bundle_id)
    if not order:
        raise HTTPException(status_code=500, detail="Failed to create order")

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    total = float(order.get("total", 0))
    currency = order.get("currency", "USD")
    order_id = order.get("id", "")
    summary = f"Checkout initiated for {bundle.get('name', 'Your Bundle')}. Total: {currency} {total:.2f}. Order ID: {order_id}. Ready for payment."
    return {
        "data": order,
        "order_id": order_id,
        "summary": summary,
        "adaptive_card": generate_checkout_card(order),
        "machine_readable": {
            "@context": "https://schema.org",
            "@type": "Order",
            "orderNumber": order_id,
            "orderId": order_id,
            "totalPrice": total,
            "priceCurrency": currency,
            "orderStatus": "CheckoutInitiated",
        },
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }


@router.post("/bundle/remove")
async def remove_item_from_bundle(request: Request, body: RemoveFromBundleBody):
    """Remove item from bundle. For Remove action on bundle card."""
    result = await remove_from_bundle(item_id=body.item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item or bundle not found")
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    summary = f"Removed item from bundle. Total: {result.get('currency', 'USD')} {float(result.get('total_price', 0)):.2f}"
    return {
        "data": result,
        "summary": summary,
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }
