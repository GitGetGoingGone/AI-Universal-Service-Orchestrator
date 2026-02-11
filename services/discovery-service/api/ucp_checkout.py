"""UCP Checkout API - Create, Get, Update, Complete, Cancel per UCP spec."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from db import (
    create_bundle_from_ucp_items,
    create_order_from_bundle,
    get_order_by_id,
    get_bundle_by_id,
    update_order_status,
)

router = APIRouter(prefix="/api/v1/ucp", tags=["UCP Checkout"])

# Default links for UCP compliance
DEFAULT_LINKS = [
    {"type": "privacy_policy", "url": "https://example.com/privacy", "title": "Privacy Policy"},
    {"type": "terms_of_service", "url": "https://example.com/terms", "title": "Terms of Service"},
]


def _order_to_ucp_checkout(order: Dict[str, Any], base_url: str = "") -> Dict[str, Any]:
    """Convert order to UCP checkout response shape."""
    order_id = str(order.get("id", ""))
    payment_status = order.get("payment_status", "pending")
    total = float(order.get("total_amount", 0))
    currency = order.get("currency", "USD")
    items = order.get("items", [])

    if payment_status == "paid":
        status = "completed"
        continue_url = None
        order_conf = {"id": order_id, "permalink_url": f"{base_url}/orders" if base_url else None}
    else:
        status = "requires_escalation"  # Buyer must complete payment via continue_url
        continue_url = f"{base_url}/pay?order_id={order_id}" if base_url else None
        order_conf = None

    line_items: List[Dict[str, Any]] = []
    for it in items:
        qty = int(it.get("quantity", 1))
        unit_price = float(it.get("unit_price", 0))
        total_price = float(it.get("total_price", unit_price * qty))
        line_items.append({
            "id": str(it.get("id", "")),
            "item": {
                "id": str(it.get("product_id", "")),
                "title": it.get("item_name", "Item"),
                "price": int(round(unit_price * 100)),
                "image_url": None,
            },
            "quantity": qty,
            "totals": [{"type": "subtotal", "amount": int(round(total_price * 100)), "currency": currency}],
        })

    totals = [{"type": "total", "amount": int(round(total * 100)), "currency": currency}]
    expires_at = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                  .replace(hour=datetime.now(timezone.utc).hour + 6).isoformat().replace("+00:00", "Z"))

    result: Dict[str, Any] = {
        "ucp": {"version": "2026-01-11", "capability": "dev.ucp.shopping.checkout"},
        "id": order_id,
        "line_items": line_items,
        "status": status,
        "currency": currency,
        "totals": totals,
        "links": DEFAULT_LINKS,
        "expires_at": expires_at,
        "payment": {
            "handlers": [{"type": "stripe", "provider": "stripe"}],
            "instruments": [],
        },
    }
    if continue_url:
        result["continue_url"] = continue_url
    if status == "requires_escalation":
        result["messages"] = [
            {"type": "info", "content": "Complete payment via the link below.", "severity": "requires_buyer_input"}
        ]
    if order_conf:
        result["order"] = order_conf
    return result


class LineItemCreate(BaseModel):
    item: Dict[str, Any]
    quantity: int = 1


class CreateCheckoutBody(BaseModel):
    line_items: List[LineItemCreate]
    buyer: Optional[Dict[str, Any]] = None
    currency: str = "USD"
    payment: Dict[str, Any]


@router.post("/checkout")
async def create_checkout(body: CreateCheckoutBody) -> Dict[str, Any]:
    """Create checkout session from UCP line items."""
    if not body.line_items:
        raise HTTPException(status_code=400, detail="line_items required")
    items = [{"item": li.item, "quantity": li.quantity} for li in body.line_items]
    bundle_id = await create_bundle_from_ucp_items(items, body.currency)
    if not bundle_id:
        raise HTTPException(status_code=400, detail="Failed to create bundle from items")
    order = await create_order_from_bundle(bundle_id)
    if not order:
        raise HTTPException(status_code=500, detail="Failed to create order")
    base_url = settings.portal_public_url or ""
    return _order_to_ucp_checkout(order, base_url)


@router.get("/checkout/{checkout_id}")
async def get_checkout(checkout_id: str) -> Dict[str, Any]:
    """Get checkout session by ID."""
    order = await get_order_by_id(checkout_id)
    if not order:
        raise HTTPException(status_code=404, detail="Checkout not found")
    base_url = settings.portal_public_url or ""
    return _order_to_ucp_checkout(order, base_url)


class LineItemUpdate(BaseModel):
    id: Optional[str] = None
    item: Dict[str, Any]
    quantity: int = 1


class UpdateCheckoutBody(BaseModel):
    line_items: List[LineItemUpdate]
    buyer: Optional[Dict[str, Any]] = None
    currency: str = "USD"
    payment: Dict[str, Any]


@router.put("/checkout/{checkout_id}")
async def update_checkout(checkout_id: str, body: UpdateCheckoutBody) -> Dict[str, Any]:
    """Update checkout - full replacement. For MVP we return current state."""
    order = await get_order_by_id(checkout_id)
    if not order:
        raise HTTPException(status_code=404, detail="Checkout not found")
    if order.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Checkout already completed")
    base_url = settings.portal_public_url or ""
    return _order_to_ucp_checkout(order, base_url)


class CompleteCheckoutBody(BaseModel):
    payment_data: Dict[str, Any]
    risk_signals: Optional[Dict[str, Any]] = None


@router.post("/checkout/{checkout_id}/complete")
async def complete_checkout(checkout_id: str, body: CompleteCheckoutBody) -> Dict[str, Any]:
    """
    Complete checkout. For MVP we require payment via continue_url.
    If payment_data contains processable payment, we could confirm here.
    For now we return requires_escalation with continue_url.
    """
    order = await get_order_by_id(checkout_id)
    if not order:
        raise HTTPException(status_code=404, detail="Checkout not found")
    if order.get("payment_status") == "paid":
        base_url = settings.portal_public_url or ""
        return _order_to_ucp_checkout(order, base_url)
    # Payment must be completed via continue_url (Stripe). Return same state.
    base_url = settings.portal_public_url or ""
    return _order_to_ucp_checkout(order, base_url)


@router.post("/checkout/{checkout_id}/cancel")
async def cancel_checkout(checkout_id: str) -> Dict[str, Any]:
    """Cancel checkout session."""
    order = await get_order_by_id(checkout_id)
    if not order:
        raise HTTPException(status_code=404, detail="Checkout not found")
    if order.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Cannot cancel completed checkout")
    await update_order_status(checkout_id, "cancelled", "cancelled")
    base_url = settings.portal_public_url or ""
    result = _order_to_ucp_checkout(order, base_url)
    result["status"] = "canceled"
    result["continue_url"] = None
    result["order"] = None
    return result
