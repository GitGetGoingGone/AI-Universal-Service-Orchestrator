"""Order queue API - accept, reject, status updates."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_partner_admin
from config import settings
from db import (
    accept_order_leg,
    get_order_leg,
    get_partner_by_id,
    list_partner_orders,
    reject_order_leg,
    update_order_leg_status,
)

router = APIRouter(prefix="/api/v1", tags=["Orders"])


def _base_context(**kwargs):
    return {"default_theme": settings.default_theme, "default_layout": settings.default_layout, **kwargs}


_tpl = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_tpl))


class AcceptBody(BaseModel):
    preparation_mins: int = 15


class RejectBody(BaseModel):
    reject_reason: str


class StatusBody(BaseModel):
    status: str
    preparation_mins: Optional[int] = None


@router.get("/partners/{partner_id}/orders", response_class=HTMLResponse)
async def orders_page(request: Request, partner_id: str):
    """Order queue page."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    orders = await list_partner_orders(partner_id)
    return templates.TemplateResponse(
        "orders.html",
        _base_context(request=request, partner=partner, orders=orders),
    )


@router.get("/partners/{partner_id}/orders/list")
async def get_orders(
    partner_id: str,
    _: str = Depends(require_partner_admin),
):
    """List orders for partner (JSON)."""
    partner = await get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    orders = await list_partner_orders(partner_id)
    return {"orders": orders}


@router.post("/partners/{partner_id}/orders/{order_id}/legs/{leg_id}/accept")
async def accept_order(
    partner_id: str,
    order_id: str,
    leg_id: str,
    body: AcceptBody,
    _: str = Depends(require_partner_admin),
):
    """Accept order with preparation time."""
    leg = await get_order_leg(leg_id, partner_id)
    if not leg or str(leg.get("order_id")) != order_id:
        raise HTTPException(status_code=404, detail="Order not found")
    result = await accept_order_leg(leg_id, partner_id, body.preparation_mins)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to accept")
    return {"message": "Order accepted"}


@router.post("/partners/{partner_id}/orders/{order_id}/legs/{leg_id}/reject")
async def reject_order(
    partner_id: str,
    order_id: str,
    leg_id: str,
    body: RejectBody,
    _: str = Depends(require_partner_admin),
):
    """Reject order with reason."""
    leg = await get_order_leg(leg_id, partner_id)
    if not leg or str(leg.get("order_id")) != order_id:
        raise HTTPException(status_code=404, detail="Order not found")
    result = await reject_order_leg(leg_id, partner_id, body.reject_reason)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to reject")
    return {"message": "Order rejected"}


@router.patch("/partners/{partner_id}/orders/{order_id}/legs/{leg_id}")
async def update_leg_status(
    partner_id: str,
    order_id: str,
    leg_id: str,
    body: StatusBody,
    _: str = Depends(require_partner_admin),
):
    """Update leg status (preparing, ready, fulfilled)."""
    leg = await get_order_leg(leg_id, partner_id)
    if not leg or str(leg.get("order_id")) != order_id:
        raise HTTPException(status_code=404, detail="Order not found")
    kwargs = {}
    if body.preparation_mins is not None:
        kwargs["preparation_mins"] = body.preparation_mins
    result = await update_order_leg_status(leg_id, partner_id, body.status, **kwargs)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update")
    return {"message": "Status updated"}
