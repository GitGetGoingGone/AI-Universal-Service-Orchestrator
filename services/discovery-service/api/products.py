"""Product discovery API - Chat-First with JSON-LD and Adaptive Cards."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query, Request

from config import settings
from db import (
    get_distinct_experience_tags,  # type: ignore[reportAttributeAccessIssue]
    get_product_by_id,  # type: ignore[reportAttributeAccessIssue]
    get_products_for_acp_export,  # type: ignore[reportAttributeAccessIssue]
    add_product_to_bundle,  # type: ignore[reportAttributeAccessIssue]
    add_products_to_bundle_bulk,  # type: ignore[reportAttributeAccessIssue]
    get_bundle_by_id,  # type: ignore[reportAttributeAccessIssue]
    remove_from_bundle,  # type: ignore[reportAttributeAccessIssue]
    replace_product_in_bundle,  # type: ignore[reportAttributeAccessIssue]
    create_order_from_bundle,  # type: ignore[reportAttributeAccessIssue]
    mask_products,  # type: ignore[reportAttributeAccessIssue]
    resolve_masked_id,  # type: ignore[reportAttributeAccessIssue]
)
from scout_engine import search
from semantic_search import semantic_search_kb_articles
from protocols.acp_compliance import validate_product_acp
from protocols.ucp_compliance import validate_product_ucp
from packages.shared.adaptive_cards import generate_product_card, generate_bundle_card, generate_checkout_card
from packages.shared.adaptive_cards.base import create_card, text_block
from packages.shared.ucp_public_product import filter_product_for_public

router = APIRouter(prefix="/api/v1", tags=["Discover"])


def _product_for_public_response(product: dict) -> dict:
    """Strip internal-only fields (experience_tags, partner_id, internal_notes) per shared allow-list."""
    return filter_product_for_public(product)


@router.get("/experience-categories")
async def get_experience_categories(request: Request):
    """Return distinct experience categories (tags) for filtering discovery (e.g. baby, celebration)."""
    categories = await get_distinct_experience_tags()
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return {
        "data": {"experience_categories": categories},
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }


class AddToBundleBody(BaseModel):
    """Request body for adding a product to a bundle."""

    product_id: str
    user_id: Optional[str] = None
    bundle_id: Optional[str] = None


class AddBulkBody(BaseModel):
    """Request body for adding multiple products to a bundle."""

    product_ids: list[str]
    user_id: Optional[str] = None
    bundle_id: Optional[str] = None
    pickup_time: Optional[str] = None
    pickup_address: Optional[str] = None
    delivery_address: Optional[str] = None
    fulfillment_fields: Optional[list[str]] = None  # Dynamic required fields per bundle


class RemoveFromBundleBody(BaseModel):
    """Request body for removing an item from a bundle."""

    item_id: str  # bundle_leg id from bundle card


class CheckoutBody(BaseModel):
    """Request body for proceeding to checkout."""

    bundle_id: str


class ReplaceInBundleBody(BaseModel):
    """Request body for replacing a product in a bundle (category refinement)."""

    bundle_id: str
    leg_id: str  # bundle_leg id to replace
    new_product_id: str


@router.get("/discover/kb")
async def discover_kb_articles(
    request: Request,
    intent: str = Query(..., description="Search query for KB articles (e.g. 'custom bundles', 'personalized letter')"),
    partner_id: Optional[str] = Query(None, description="Filter by partner"),
    exclude_partner_id: Optional[str] = Query(None, description="Exclude partner"),
    limit: int = Query(20, ge=1, le=50),
):
    """
    Discover partner KB articles by semantic similarity.
    Returns articles whose title+content embedding matches the query (e.g. offerings, policies).
    Run embedding backfill with type=kb_articles first so articles have embeddings.
    """
    articles = await semantic_search_kb_articles(
        query=intent,
        limit=limit,
        partner_id=partner_id,
        exclude_partner_id=exclude_partner_id,
    )
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return {
        "data": {
            "kb_articles": articles,
            "count": len(articles),
        },
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }


@router.get("/discover")
async def discover_products(
    request: Request,
    intent: str = Query(..., description="Search query (e.g. 'flowers', 'chocolates')"),
    location: Optional[str] = Query(None, description="Optional location filter"),
    partner_id: Optional[str] = Query(None, description="Filter by partner"),
    exclude_partner_id: Optional[str] = Query(None, description="Exclude partner (for re-sourcing)"),
    limit: int = Query(20, ge=1, le=100),
    budget_max: Optional[int] = Query(None, ge=0, description="Max price in cents (e.g. 5000 for $50)"),
    experience_tag: Optional[str] = Query(None, description="Filter/boost by experience category (e.g. baby, celebration)"),
    experience_tags: Optional[List[str]] = Query(None, description="Filter by multiple experience categories (AND semantics; e.g. luxury, travel-friendly)"),
    include_kb_articles: bool = Query(False, description="When true, also return semantically matched partner KB articles"),
):
    """
    Discover products by intent/query.
    Chat-First: Returns JSON-LD and Adaptive Card for AI agents.
    Optionally include partner KB articles (semantic match) via include_kb_articles=true.
    """
    products = await search(
        query=intent, limit=limit * 2 if budget_max else limit,
        partner_id=partner_id, exclude_partner_id=exclude_partner_id,
        experience_tag=experience_tag,
        experience_tags=experience_tags,
    )
    if settings.id_masking_enabled and products:
        products = await mask_products(products, source="local")
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

    # Multi-Agent encapsulation: do not expose experience_tags to Planner/UCP
    products_public = [_product_for_public_response(p) for p in products]

    # Build JSON-LD ItemList (schema.org)
    item_list_elements = []
    for p in products_public:
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

    out: Dict[str, Any] = {
        "data": {
            "products": products_public,
            "count": len(products_public),
        },
        "machine_readable": {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "numberOfItems": len(products_public),
            "itemListElement": item_list_elements,
        },
        "adaptive_card": generate_product_card(products_public[:5]),
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
        },
    }
    if include_kb_articles:
        kb_articles = await semantic_search_kb_articles(
            query=intent,
            limit=10,
            partner_id=partner_id,
            exclude_partner_id=exclude_partner_id,
        )
        out["data"]["kb_articles"] = kb_articles
    return out


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
    """Get product by ID. For View Details action. Accepts masked id (uso_*) when ID masking is enabled."""
    internal_id = product_id
    if str(product_id).startswith("uso_"):
        resolved = resolve_masked_id(product_id)
        if resolved:
            internal_id = resolved[0]
        else:
            raise HTTPException(status_code=404, detail="Product not found")
    product = await get_product_by_id(internal_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if settings.id_masking_enabled and str(product_id).startswith("uso_"):
        product = dict(product)
        product["id"] = product_id
        product.pop("partner_id", None)
    product_public = _product_for_public_response(product)
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return {
        "data": product_public,
        "machine_readable": {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product_public.get("name"),
            "description": product_public.get("description"),
            "offers": {
                "@type": "Offer",
                "price": float(product_public.get("price", 0)),
                "priceCurrency": product_public.get("currency", "USD"),
            },
            "identifier": str(product_public.get("id")),
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
    if order.get("error") == "fulfillment_required":
        raise HTTPException(
            status_code=400,
            detail=order.get("message", "Pickup time, pickup address, and delivery address are required before checkout."),
        )

    # Order → Task Queue integration: create vendor tasks for the new order
    order_id = order.get("id", "")
    task_queue_url = getattr(settings, "task_queue_service_url", "") or ""
    if order_id and task_queue_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{task_queue_url.rstrip('/')}/api/v1/orders/{order_id}/tasks"
                )
        except Exception:
            pass

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


@router.post("/bundle/add-bulk")
async def add_to_bundle_bulk(request: Request, body: AddBulkBody):
    """Add multiple products to a bundle. For Add curated bundle action."""
    fulfillment = None
    if body.pickup_time or body.pickup_address or body.delivery_address or body.fulfillment_fields:
        fulfillment = {
            "pickup_time": body.pickup_time or "",
            "pickup_address": body.pickup_address or "",
            "delivery_address": body.delivery_address or "",
            "required_fields": body.fulfillment_fields or ["pickup_time", "pickup_address", "delivery_address"],
        }
    result = await add_products_to_bundle_bulk(
        product_ids=body.product_ids,
        user_id=body.user_id,
        bundle_id=body.bundle_id,
        fulfillment_details=fulfillment,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to add products to bundle (products not found or error)")
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    products_added = result.get("products_added", [])
    total = float(result.get("total_price", 0))
    curr = result.get("currency", "USD")
    summary = f"Added {len(products_added)} item(s) to bundle. Total: {curr} {total:.2f}"
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


@router.post("/bundle/replace")
async def replace_in_bundle(request: Request, body: ReplaceInBundleBody):
    """Replace a product in bundle (category refinement). Removes leg, adds new product."""
    result = await replace_product_in_bundle(
        bundle_id=body.bundle_id,
        leg_id_to_replace=body.leg_id,
        new_product_id=body.new_product_id,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to replace product in bundle")
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    summary = f"Replaced with {result.get('product_added', 'product')}. Total: {result.get('currency', 'USD')} {float(result.get('total_price', 0)):.2f}"
    return {
        "data": result,
        "summary": summary,
        "adaptive_card": create_card(
            body=[text_block(summary)],
            actions=[
                {"type": "Action.Submit", "title": "View Bundle", "data": {"action": "view_bundle", "bundle_id": str(body.bundle_id)}},
            ],
        ),
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
