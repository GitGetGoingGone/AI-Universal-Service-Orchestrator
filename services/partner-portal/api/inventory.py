"""Inventory API - stock levels, low-stock alerts."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import (
    get_partner_by_id,
    get_product_by_id,
    get_product_inventory,
    list_products,
    update_product,
    upsert_product_inventory,
)

router = APIRouter(prefix="/api/v1", tags=["Inventory"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class InventoryBody(BaseModel):
    quantity: int
    low_stock_threshold: int = 5
    auto_unlist_when_zero: bool = True


@router.get("/partners/{partner_id}/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, partner_id: str):
    """Inventory page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    products = await list_products(partner_id)
    inv_data = []
    for p in products:
        inv = await get_product_inventory(p["id"])
        inv_data.append({"product": p, "inventory": inv})
    return templates.TemplateResponse(
        "inventory.html",
        _base_context(request=request, partner=partner, inv_data=inv_data),
    )


@router.get("/partners/{partner_id}/products/{product_id}/inventory")
async def get_inventory(
    partner_id: str,
    product_id: str,
    _: str = Depends(require_partner_admin),
):
    """Get product inventory (JSON)."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    inv = await get_product_inventory(product_id)
    return {"inventory": inv}


@router.put("/partners/{partner_id}/products/{product_id}/inventory")
async def update_inventory(
    partner_id: str,
    product_id: str,
    body: InventoryBody,
    _: str = Depends(require_partner_admin),
):
    """Update product inventory."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    inv = await upsert_product_inventory(
        product_id=product_id,
        quantity=body.quantity,
        low_stock_threshold=body.low_stock_threshold,
        auto_unlist_when_zero=body.auto_unlist_when_zero,
    )
    if not inv:
        raise HTTPException(status_code=500, detail="Failed to update")
    if body.auto_unlist_when_zero and body.quantity <= 0:
        await update_product(product_id, partner_id, is_available=False)
    return {"message": "Inventory updated", "inventory": inv}


class AvailabilityToggleBody(BaseModel):
    is_available: bool


@router.patch("/partners/{partner_id}/products/{product_id}/availability")
async def toggle_availability(
    partner_id: str,
    product_id: str,
    body: AvailabilityToggleBody,
    _: str = Depends(require_partner_admin),
):
    """Toggle product out-of-stock (availability)."""
    product = await get_product_by_id(product_id, partner_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await update_product(product_id, partner_id, is_available=body.is_available)
    return {"message": "Availability updated", "is_available": body.is_available}
