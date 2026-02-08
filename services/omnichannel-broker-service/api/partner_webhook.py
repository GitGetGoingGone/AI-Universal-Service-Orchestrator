"""Partner webhook API - inbound (partner responses) and outbound (change requests)."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import (
    get_partner_webhook,
    create_negotiation,
    get_negotiation,
    update_negotiation_status,
    add_negotiation_message,
)
from partner_notifier import notify_partner
from state_machine import can_transition
from clients import trigger_recovery

router = APIRouter(tags=["Partner Webhook"])


class PartnerResponseBody(BaseModel):
    """Partner response to change request."""

    negotiation_id: str
    response: str  # "accept" | "reject"
    rejection_reason: Optional[str] = None
    counter_offer: Optional[Dict[str, Any]] = None


class CreateChangeRequestBody(BaseModel):
    """Create a change request (from Orchestrator)."""

    order_id: str
    order_leg_id: str
    partner_id: str
    original_item: Dict[str, Any]
    requested_change: Dict[str, Any]
    respond_by: Optional[str] = None


@router.post("/webhooks/partner")
async def partner_response(body: PartnerResponseBody):
    """
    Partner responds to change request (accept/reject).
    On reject, triggers Re-Sourcing Service.
    """
    negotiation = await get_negotiation(body.negotiation_id)
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    current_status = negotiation.get("status", "")
    new_status = "accepted" if body.response.lower() == "accept" else "rejected"

    if not can_transition(current_status, new_status):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from {current_status} to {new_status}",
        )

    await update_negotiation_status(body.negotiation_id, new_status, {"response": body.response})
    await add_negotiation_message(
        body.negotiation_id,
        "partner_response",
        f"Partner {body.response}: {body.rejection_reason or ''}",
        channel="api",
        metadata={"response": body.response, "rejection_reason": body.rejection_reason},
    )

    if body.response.lower() == "reject":
        # Trigger Autonomous Re-Sourcing
        rejection_payload = {
            "rejection_reason": body.rejection_reason,
            "counter_offer": body.counter_offer,
            "original_request": negotiation.get("original_request", {}),
        }
        success, _ = await trigger_recovery(body.negotiation_id, rejection_payload)
        if not success:
            # Log but don't fail - recovery may be retried
            pass

    return {"status": new_status, "negotiation_id": body.negotiation_id}


@router.post("/api/v1/change-request")
async def create_change_request(body: CreateChangeRequestBody):
    """
    Create a change request and notify partner via webhook.
    Called by Orchestrator when user requests a change.
    """
    webhook_url = await get_partner_webhook(body.partner_id)
    if not webhook_url:
        raise HTTPException(
            status_code=400,
            detail="Partner has no webhook URL configured. Configure in Partner Portal.",
        )

    original_request = {
        "original_item": body.original_item,
        "requested_change": body.requested_change,
        "respond_by": body.respond_by,
    }

    negotiation = await create_negotiation(
        order_id=body.order_id,
        order_leg_id=body.order_leg_id,
        partner_id=body.partner_id,
        negotiation_type="product_change",
        original_request=original_request,
    )
    if not negotiation:
        raise HTTPException(status_code=500, detail="Failed to create negotiation")

    payload = {
        "negotiation_id": str(negotiation["id"]),
        "order_id": body.order_id,
        "order_leg_id": body.order_leg_id,
        "request_type": "product_change",
        "original_item": body.original_item,
        "requested_change": body.requested_change,
        "respond_by": body.respond_by or datetime.now(timezone.utc).isoformat(),
    }

    ok, err = await notify_partner(webhook_url, payload)
    if not ok:
        await update_negotiation_status(str(negotiation["id"]), "escalated")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to notify partner: {err}",
        )

    return {
        "negotiation_id": str(negotiation["id"]),
        "status": "awaiting_partner_reply",
        "message": "Change request sent to partner",
    }
