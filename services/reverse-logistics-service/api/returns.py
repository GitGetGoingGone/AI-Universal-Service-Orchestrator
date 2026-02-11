"""Reverse Logistics API (Module 17) - Returns, refunds, restocking."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import (
    create_return_request,
    list_return_requests,
    get_return_request,
    approve_return_request,
    reject_return_request,
    create_refund,
    create_restock_event,
    complete_return_request,
)

router = APIRouter(prefix="/api/v1", tags=["Reverse Logistics"])


class CreateReturnBody(BaseModel):
    order_id: str
    partner_id: str
    reason: str = "other"
    reason_detail: Optional[str] = None
    order_leg_id: Optional[str] = None
    requester_id: Optional[str] = None
    photo_url: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    refund_amount_cents: Optional[int] = None


class RestockBody(BaseModel):
    product_id: str
    quantity: int


@router.post("/returns")
def create_return(body: CreateReturnBody) -> Dict[str, Any]:
    """Create a return request (RMA)."""
    ret = create_return_request(
        order_id=body.order_id,
        partner_id=body.partner_id,
        reason=body.reason,
        reason_detail=body.reason_detail,
        order_leg_id=body.order_leg_id,
        requester_id=body.requester_id,
        photo_url=body.photo_url,
        items=body.items,
        refund_amount_cents=body.refund_amount_cents,
    )
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to create return request")
    return ret


@router.get("/returns")
def list_returns(
    order_id: Optional[str] = Query(None),
    partner_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """List return requests with optional filters."""
    data = list_return_requests(order_id=order_id, partner_id=partner_id, status=status)
    return {"returns": data, "count": len(data)}


@router.get("/returns/{return_id}")
def get_return(return_id: str) -> Dict[str, Any]:
    """Get a single return request."""
    ret = get_return_request(return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    return ret


@router.post("/returns/{return_id}/approve")
def approve_return(return_id: str) -> Dict[str, Any]:
    """Approve a return request."""
    ret = approve_return_request(return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    return ret


@router.post("/returns/{return_id}/reject")
def reject_return(return_id: str) -> Dict[str, Any]:
    """Reject a return request."""
    ret = reject_return_request(return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    return ret


@router.post("/returns/{return_id}/refund")
def process_refund(return_id: str) -> Dict[str, Any]:
    """Process refund for an approved return. Creates refund record."""
    ret = get_return_request(return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    if ret.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Return must be approved before refund")
    amount = ret.get("refund_amount_cents") or 0
    if amount <= 0:
        raise HTTPException(status_code=400, detail="refund_amount_cents required on return request")
    refund = create_refund(
        return_request_id=return_id,
        order_id=ret["order_id"],
        amount_cents=amount,
        currency=ret.get("currency", "USD"),
    )
    if not refund:
        raise HTTPException(status_code=500, detail="Failed to create refund")
    complete_return_request(return_id)
    return {"refund": refund, "return_request": get_return_request(return_id)}


@router.post("/returns/{return_id}/restock")
def restock(return_id: str, body: RestockBody) -> Dict[str, Any]:
    """Create restock event for an approved return."""
    ret = get_return_request(return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    if ret.get("status") != "approved" and ret.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Return must be approved before restock")
    if body.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be positive")
    event = create_restock_event(
        return_request_id=return_id,
        product_id=body.product_id,
        quantity=body.quantity,
    )
    if not event:
        raise HTTPException(status_code=500, detail="Failed to create restock event")
    return event
