"""Order status API for AI agents and MCP tools."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from db import get_order_by_id

router = APIRouter(prefix="/api/v1", tags=["Orders"])


@router.get("/orders/{order_id}/status")
async def get_order_status(order_id: str) -> Dict[str, Any]:
    """
    Get order status for AI agents (track_order tool).
    Returns order id, status, payment_status, total, items.
    """
    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": order.get("id"),
        "bundle_id": order.get("bundle_id"),
        "status": order.get("status", "unknown"),
        "payment_status": order.get("payment_status", "pending"),
        "total_amount": float(order.get("total_amount", 0)),
        "currency": order.get("currency", "USD"),
        "created_at": order.get("created_at"),
        "items": [
            {
                "id": it.get("id"),
                "product_id": it.get("product_id"),
                "item_name": it.get("item_name"),
                "quantity": it.get("quantity"),
                "unit_price": float(it.get("unit_price", 0)),
                "total_price": float(it.get("total_price", 0)),
            }
            for it in order.get("items", [])
        ],
    }
