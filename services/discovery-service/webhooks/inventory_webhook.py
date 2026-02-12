"""Inventory update webhook - syncs product_inventory, notifies chat threads."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from config import settings

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class InventoryUpdateBody(BaseModel):
    """Inventory update payload."""

    product_id: str
    partner_id: Optional[str] = None
    event: str  # "stock_change", "price_change", "availability_change"
    previous_value: Optional[Any] = None
    new_value: Optional[Any] = None
    quantity: Optional[int] = None
    reserved_quantity: Optional[int] = None
    thread_ids: Optional[List[str]] = None


def _upsert_product_inventory(
    product_id: str,
    partner_id: Optional[str],
    quantity: Optional[int] = None,
    reserved_quantity: Optional[int] = None,
) -> bool:
    """Upsert product_inventory. Returns True if successful."""
    try:
        from db import get_supabase
        client = get_supabase()
        if not client:
            return False
        existing = client.table("product_inventory").select("id, quantity, reserved_quantity").eq("product_id", product_id).limit(1).execute()
        row = existing.data[0] if existing.data else None
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        payload = {"product_id": product_id, "sync_method": "webhook", "last_synced_at": now, "updated_at": now}
        if partner_id:
            payload["partner_id"] = partner_id
        if quantity is not None:
            payload["quantity"] = quantity
        if reserved_quantity is not None:
            payload["reserved_quantity"] = reserved_quantity
        if row:
            client.table("product_inventory").update(payload).eq("id", row["id"]).execute()
        else:
            payload.setdefault("quantity", quantity or 0)
            payload.setdefault("reserved_quantity", reserved_quantity or 0)
            client.table("product_inventory").insert(payload).execute()
        return True
    except Exception:
        return False


@router.post("/inventory")
async def inventory_webhook(
    body: InventoryUpdateBody,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    """
    Receive inventory/availability updates from partners.
    Upserts product_inventory. Optionally pushes to webhook-service for thread_ids.
    """
    quantity = body.quantity
    if body.event == "stock_change" and body.new_value is not None and quantity is None:
        quantity = int(body.new_value) if isinstance(body.new_value, (int, float)) else None

    if quantity is not None:
        _upsert_product_inventory(
            body.product_id,
            body.partner_id,
            quantity=quantity,
            reserved_quantity=body.reserved_quantity,
        )

    if body.thread_ids and settings.webhook_service_url:
        import httpx
        narrative = f"Product {body.product_id}: {body.event}"
        if body.previous_value is not None and body.new_value is not None:
            narrative = f"{body.event}: {body.previous_value} → {body.new_value}"
        for tid in body.thread_ids[:5]:
            try:
                async with httpx.AsyncClient(timeout=10.0) as c:
                    await c.post(
                        f"{settings.webhook_service_url}/api/v1/webhooks/chat/chatgpt/{tid}",
                        json={"narrative": narrative, "metadata": {"product_id": body.product_id}},
                    )
            except Exception:
                pass

    return {"received": True, "product_id": body.product_id, "event": body.event}
