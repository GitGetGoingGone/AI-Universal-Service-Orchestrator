"""HubNegotiator & Bidding API (Module 10)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import (
    create_rfp,
    list_rfps,
    get_rfp,
    get_bids_for_rfp,
    submit_bid,
    select_winning_bid,
    get_hubs_with_capacity,
    add_hub_capacity,
)

router = APIRouter(prefix="/api/v1", tags=["HubNegotiator"])


class CreateRFPBody(BaseModel):
    order_id: Optional[str] = None
    bundle_id: Optional[str] = None
    request_type: str = "assembly"
    title: str = "RFP"
    description: Optional[str] = None
    delivery_address: Optional[Dict[str, Any]] = None
    deadline: str = ""
    compensation_cents: Optional[int] = None


class SubmitBidBody(BaseModel):
    hub_partner_id: str = ""
    amount_cents: int = 0
    proposed_completion_at: Optional[str] = None


class SelectWinnerBody(BaseModel):
    bid_id: str = ""


class CapacityBody(BaseModel):
    partner_id: str = ""
    available_from: str = ""
    available_until: str = ""
    capacity_slots: int = 1


@router.post("/rfps")
def create_rfp_endpoint(body: CreateRFPBody) -> Dict[str, Any]:
    if not body.deadline:
        raise HTTPException(status_code=400, detail="deadline required")
    rfp = create_rfp(
        order_id=body.order_id,
        bundle_id=body.bundle_id,
        request_type=body.request_type,
        title=body.title,
        description=body.description,
        delivery_address=body.delivery_address,
        deadline=body.deadline,
        compensation_cents=body.compensation_cents,
    )
    if not rfp:
        raise HTTPException(status_code=500, detail="Failed to create RFP")
    return rfp


@router.get("/rfps")
def list_rfps_endpoint(status: str = Query("open", description="open | closed")) -> Dict[str, Any]:
    rfps = list_rfps(status=status)
    return {"rfps": rfps, "count": len(rfps)}


@router.get("/rfps/{rfp_id}")
def get_rfp_endpoint(rfp_id: str) -> Dict[str, Any]:
    rfp = get_rfp(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


@router.get("/rfps/{rfp_id}/bids")
def list_bids_endpoint(rfp_id: str) -> Dict[str, Any]:
    if not get_rfp(rfp_id):
        raise HTTPException(status_code=404, detail="RFP not found")
    bids = get_bids_for_rfp(rfp_id)
    return {"bids": bids, "count": len(bids)}


@router.post("/rfps/{rfp_id}/bids")
def submit_bid_endpoint(rfp_id: str, body: SubmitBidBody) -> Dict[str, Any]:
    if not body.hub_partner_id or body.amount_cents < 0:
        raise HTTPException(status_code=400, detail="hub_partner_id and amount_cents required")
    bid = submit_bid(
        rfp_id=rfp_id,
        hub_partner_id=body.hub_partner_id,
        amount_cents=body.amount_cents,
        proposed_completion_at=body.proposed_completion_at,
    )
    if not bid:
        raise HTTPException(status_code=400, detail="RFP not open or duplicate bid")
    return bid


@router.post("/rfps/{rfp_id}/select-winner")
def select_winner_endpoint(rfp_id: str, body: SelectWinnerBody) -> Dict[str, Any]:
    if not body.bid_id:
        raise HTTPException(status_code=400, detail="bid_id required")
    rfp = select_winning_bid(rfp_id, body.bid_id)
    if not rfp:
        raise HTTPException(status_code=400, detail="RFP not open or bid not found")
    return rfp


@router.get("/rfps/{rfp_id}/capacity-match")
def capacity_match_endpoint(rfp_id: str) -> Dict[str, Any]:
    """Return hub partner_ids that have capacity for this RFP's deadline window."""
    rfp = get_rfp(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    deadline = rfp.get("deadline")
    if not deadline:
        return {"partner_ids": []}
    from datetime import datetime, timedelta
    try:
        dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        window_start = (dt - timedelta(hours=24)).isoformat()
        window_end = (dt + timedelta(hours=2)).isoformat()
    except Exception:
        window_start = deadline
        window_end = deadline
    partner_ids = get_hubs_with_capacity(window_start, window_end)
    return {"partner_ids": partner_ids, "rfp_id": rfp_id}


@router.post("/hub-capacity")
def add_capacity_endpoint(body: CapacityBody) -> Dict[str, Any]:
    if not body.partner_id or not body.available_from or not body.available_until:
        raise HTTPException(status_code=400, detail="partner_id, available_from, available_until required")
    row = add_hub_capacity(
        partner_id=body.partner_id,
        available_from=body.available_from,
        available_until=body.available_until,
        capacity_slots=body.capacity_slots,
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to add capacity")
    return row
