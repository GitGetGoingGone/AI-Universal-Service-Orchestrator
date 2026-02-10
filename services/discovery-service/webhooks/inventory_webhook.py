"""Inventory update webhook - notifies chat threads of product availability changes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class InventoryUpdateBody(BaseModel):
    """Inventory update payload."""

    product_id: str
    partner_id: Optional[str] = None
    event: str  # "stock_change", "price_change", "availability_change"
    previous_value: Optional[Any] = None
    new_value: Optional[Any] = None
    thread_ids: Optional[List[str]] = None  # Chat thread IDs to notify


@router.post("/inventory")
async def inventory_webhook(
    body: InventoryUpdateBody,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    """
    Receive inventory/availability updates from partners.
    Forwards to webhook-service for push to chat threads (ChatGPT, Gemini).
    """
    # TODO: Verify X-Webhook-Secret when configured
    # TODO: Call webhook-service to push to thread_ids
    # For now, log and return 202
    return {
        "received": True,
        "product_id": body.product_id,
        "event": body.event,
        "message": "Inventory update received; push to chat threads when webhook-service configured",
    }
